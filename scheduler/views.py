import json

from django.db.models import Count, Prefetch, Q
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .models import Course, Meeting, Section
from .solver import DAYS, Preferences, conflicting_pairs, format_minutes, parse_hhmm, solve

MAX_COURSES = 8


def index(request: HttpRequest):
    return render(request, "scheduler/index.html")


@require_GET
def course_search(request: HttpRequest) -> JsonResponse:
    q = request.GET.get("q", "").strip()
    courses = Course.objects.annotate(section_count=Count("sections"))
    if q:
        courses = courses.filter(Q(code__icontains=q) | Q(title__icontains=q))
    data = [
        {"code": c.code, "title": c.title, "credits": c.credits, "sections": c.section_count}
        for c in courses[:25]
    ]
    return JsonResponse({"results": data})


def _bad_request(message: str) -> JsonResponse:
    return JsonResponse({"error": message}, status=400)


@require_POST
def generate_schedules(request: HttpRequest) -> JsonResponse:
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return _bad_request("Body must be JSON.")

    codes = body.get("courses")
    if not isinstance(codes, list) or not codes or not all(isinstance(c, str) for c in codes):
        return _bad_request("courses must be a non-empty list of course codes.")
    codes = list(dict.fromkeys(c.strip().upper() for c in codes))
    if len(codes) > MAX_COURSES:
        return _bad_request(f"Choose at most {MAX_COURSES} courses.")

    try:
        prefs = Preferences(
            earliest_start=parse_hhmm(body["earliest"]) if body.get("earliest") else None,
            latest_end=parse_hhmm(body["latest"]) if body.get("latest") else None,
            days_off=frozenset(d for d in body.get("daysOff", []) if d in DAYS),
            include_full=bool(body.get("includeFull", False)),
            max_results=min(int(body.get("limit", 20)), 50),
        )
    except (ValueError, TypeError):
        return _bad_request("earliest/latest must be HH:MM and limit a number.")

    known = set(Course.objects.filter(code__in=codes).values_list("code", flat=True))
    unknown = [code for code in codes if code not in known]
    if unknown:
        return _bad_request(f"Unknown course(s): {', '.join(unknown)}")

    sections = (
        Section.objects.filter(course__code__in=codes)
        .select_related("course")
        .prefetch_related(Prefetch("meetings", queryset=Meeting.objects.order_by("day", "start")))
    )
    options: dict[str, list] = {code: [] for code in codes}
    for section in sections:
        options[section.course.code].append(section.to_option())

    result = solve(options, prefs)
    payload = {
        "count": len(result.schedules),
        "explored": result.explored,
        "truncated": result.truncated,
        "unsatisfiable": result.unsatisfiable_courses,
        "schedules": [
            {
                "crns": s.crns,
                "daysOnCampus": s.days_on_campus,
                "gapMinutes": s.gap_minutes,
                "sections": [
                    {
                        "course": sec.course_code,
                        "crn": sec.crn,
                        "full": sec.is_full,
                        "meetings": [
                            {"day": t.day, "start": format_minutes(t.start), "end": format_minutes(t.end)}
                            for t in sec.slots
                        ],
                    }
                    for sec in s.sections
                ],
            }
            for s in result.schedules
        ],
    }
    if not result.schedules and not result.unsatisfiable_courses:
        payload["conflicts"] = [list(p) for p in conflicting_pairs(options)]
    return JsonResponse(payload)
