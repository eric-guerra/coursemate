"""Conflict-free schedule generation.

Pure Python with no Django imports, so it can be unit-tested and reused. Given the
candidate sections for each requested course, it enumerates every combination where
no two meetings overlap and that satisfies the student's preferences, then ranks them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

DAYS = "MTWRF"


@dataclass(frozen=True)
class TimeSlot:
    day: str        # one of DAYS
    start: int      # minutes after midnight
    end: int

    def overlaps(self, other: "TimeSlot") -> bool:
        return self.day == other.day and self.start <= other.end and other.start <= self.end


@dataclass(frozen=True)
class SectionOption:
    section_id: int
    course_code: str
    crn: str
    slots: tuple[TimeSlot, ...]
    is_full: bool = False


@dataclass(frozen=True)
class Preferences:
    earliest_start: int | None = None   # minutes; no class may start before this
    latest_end: int | None = None       # minutes; no class may end after this
    days_off: frozenset[str] = frozenset()
    include_full: bool = False
    max_results: int = 20


@dataclass
class Schedule:
    sections: list[SectionOption]
    days_on_campus: int = 0
    gap_minutes: int = 0
    score: float = 0.0

    @property
    def crns(self) -> list[str]:
        return [s.crn for s in self.sections]


@dataclass
class SolveResult:
    schedules: list[Schedule]
    explored: int
    truncated: bool
    unsatisfiable_courses: list[str] = field(default_factory=list)


# Hard cap on search nodes so a pathological request can't hang a worker.
MAX_EXPLORED = 200_000


def parse_hhmm(value: str) -> int:
    hours, minutes = value.split(":")
    h, m = int(hours), int(minutes)
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"invalid time {value!r}")
    return h * 60 + m


def format_minutes(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def fits_preferences(option: SectionOption, prefs: Preferences) -> bool:
    if option.is_full and not prefs.include_full:
        return False
    for slot in option.slots:
        if slot.day in prefs.days_off:
            return False
        if prefs.earliest_start is not None and slot.start < prefs.earliest_start:
            return False
        if prefs.latest_end is not None and slot.end > prefs.latest_end:
            return False
    return True


def sections_conflict(a: SectionOption, b: SectionOption) -> bool:
    return any(x.overlaps(y) for x in a.slots for y in b.slots)


def score_schedule(sections: list[SectionOption]) -> Schedule:
    """Fewer days on campus is better; less idle time between classes breaks ties."""
    by_day: dict[str, list[TimeSlot]] = {}
    for section in sections:
        for slot in section.slots:
            by_day.setdefault(slot.day, []).append(slot)

    gap = 0
    for slots in by_day.values():
        slots.sort(key=lambda s: s.start)
        for prev, nxt in zip(slots, slots[1:]):
            gap += max(0, nxt.start - prev.end)

    days = len(by_day)
    return Schedule(sections=sections, days_on_campus=days, gap_minutes=gap, score=days * 1000 + gap)


def solve(options_by_course: dict[str, list[SectionOption]], prefs: Preferences = Preferences()) -> SolveResult:
    filtered = {code: [o for o in opts if fits_preferences(o, prefs)] for code, opts in options_by_course.items()}
    unsatisfiable = sorted(code for code, opts in filtered.items() if not opts)
    if unsatisfiable:
        return SolveResult(schedules=[], explored=0, truncated=False, unsatisfiable_courses=unsatisfiable)

    # Most-constrained course first: prunes the search tree earliest.
    order = sorted(filtered, key=lambda code: len(filtered[code]))
    found: list[Schedule] = []
    explored = 0
    truncated = False
    chosen: list[SectionOption] = []

    def backtrack(depth: int) -> None:
        nonlocal explored, truncated
        if truncated:
            return
        if depth == len(order):
            found.append(score_schedule(list(chosen)))
            return
        for option in filtered[order[depth]]:
            explored += 1
            if explored > MAX_EXPLORED:
                truncated = True
                return
            if any(sections_conflict(option, other) for other in chosen):
                continue
            chosen.append(option)
            backtrack(depth + 1)
            chosen.pop()

    backtrack(0)
    found.sort(key=lambda s: (s.score, s.crns))
    return SolveResult(schedules=found[: prefs.max_results], explored=explored, truncated=truncated)


def conflicting_pairs(options_by_course: dict[str, list[SectionOption]]) -> list[tuple[str, str]]:
    """Course pairs where *every* section combination conflicts: useful to explain empty results."""
    pairs = []
    for (a, opts_a), (b, opts_b) in combinations(sorted(options_by_course.items()), 2):
        if opts_a and opts_b and all(sections_conflict(x, y) for x in opts_a for y in opts_b):
            pairs.append((a, b))
    return pairs
