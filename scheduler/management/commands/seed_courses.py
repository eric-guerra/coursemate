from datetime import time

from django.core.management.base import BaseCommand
from django.db import transaction

from scheduler.models import Course, Meeting, Section

# (code, title, dept, credits, [(crn, instructor, capacity, enrolled, days, start, end, room)])
CATALOG = [
    ("COSC 1430", "Introduction to Programming", "COSC", 3, [
        ("10001", "Dr. Patel", 60, 41, "MWF", "09:00", "09:50", "PGH 232"),
        ("10002", "Dr. Patel", 60, 60, "MWF", "11:00", "11:50", "PGH 232"),
        ("10003", "Dr. Nguyen", 45, 12, "TR", "13:00", "14:20", "SEC 104"),
    ]),
    ("COSC 2436", "Programming and Data Structures", "COSC", 3, [
        ("10101", "Dr. Kim", 50, 49, "MW", "10:00", "11:20", "PGH 563"),
        ("10102", "Dr. Kim", 50, 20, "TR", "10:00", "11:20", "PGH 563"),
    ]),
    ("COSC 3320", "Algorithms and Data Structures", "COSC", 3, [
        ("10201", "Dr. Alvarez", 40, 31, "TR", "08:30", "09:50", "SR1 117"),
        ("10202", "Dr. Alvarez", 40, 18, "MW", "14:30", "15:50", "SR1 117"),
    ]),
    ("COSC 3380", "Database Systems", "COSC", 3, [
        ("10301", "Dr. Chen", 55, 50, "TR", "11:30", "12:50", "PGH 232"),
        ("10302", "Dr. Chen", 55, 10, "F", "09:00", "11:50", "PGH 232"),
    ]),
    ("MATH 2318", "Linear Algebra", "MATH", 3, [
        ("20101", "Dr. Okafor", 70, 65, "MWF", "10:00", "10:50", "AH 2"),
        ("20102", "Dr. Okafor", 70, 30, "TR", "14:30", "15:50", "AH 2"),
    ]),
    ("MATH 3336", "Discrete Mathematics", "MATH", 3, [
        ("20201", "Dr. Silva", 60, 22, "MWF", "12:00", "12:50", "SEC 202"),
        ("20202", "Dr. Silva", 60, 59, "TR", "10:00", "11:20", "SEC 202"),
    ]),
    ("ENGL 1302", "First-Year Writing II", "ENGL", 3, [
        ("30101", "Prof. Rivera", 25, 25, "MW", "08:30", "09:50", "AH 110"),
        ("30102", "Prof. Rivera", 25, 14, "TR", "16:00", "17:20", "AH 110"),
    ]),
]


def parse(value: str) -> time:
    h, m = value.split(":")
    return time(int(h), int(m))


class Command(BaseCommand):
    help = "Load a sample course catalog (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        sections = 0
        for code, title, dept, credits, section_rows in CATALOG:
            course, _ = Course.objects.update_or_create(
                code=code, defaults={"title": title, "department": dept, "credits": credits}
            )
            for crn, instructor, capacity, enrolled, days, start, end, room in section_rows:
                section, _ = Section.objects.update_or_create(
                    crn=crn,
                    defaults={"course": course, "instructor": instructor, "capacity": capacity, "enrolled": enrolled},
                )
                section.meetings.all().delete()
                Meeting.objects.bulk_create(
                    Meeting(section=section, day=d, start=parse(start), end=parse(end), location=room) for d in days
                )
                sections += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(CATALOG)} courses, {sections} sections."))
