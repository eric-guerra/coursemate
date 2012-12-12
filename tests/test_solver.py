from scheduler.solver import (
    Preferences,
    SectionOption,
    TimeSlot,
    conflicting_pairs,
    format_minutes,
    parse_hhmm,
    solve,
)

import pytest


def opt(sid, course, *slots, full=False):
    return SectionOption(
        section_id=sid,
        course_code=course,
        crn=str(sid),
        slots=tuple(TimeSlot(d, parse_hhmm(s), parse_hhmm(e)) for d, s, e in slots),
        is_full=full,
    )


def mwf(start, end):
    return [("M", start, end), ("W", start, end), ("F", start, end)]


def tr(start, end):
    return [("T", start, end), ("R", start, end)]


def test_overlap_is_half_open():
    a = TimeSlot("M", 600, 650)
    assert a.overlaps(TimeSlot("M", 620, 700))
    assert not a.overlaps(TimeSlot("M", 650, 700))  # back-to-back is fine
    assert not a.overlaps(TimeSlot("T", 600, 650))


def test_finds_all_conflict_free_combinations():
    options = {
        "A": [opt(1, "A", *mwf("09:00", "09:50")), opt(2, "A", *tr("09:00", "10:20"))],
        "B": [opt(3, "B", *mwf("09:00", "09:50")), opt(4, "B", *mwf("10:00", "10:50"))],
    }
    result = solve(options)
    combos = sorted(tuple(sorted(s.crns)) for s in result.schedules)
    # 1+3 clash; 1+4, 2+3, 2+4 are fine
    assert combos == [("1", "4"), ("2", "3"), ("2", "4")]


def test_ranks_fewer_days_then_smaller_gaps_first():
    options = {
        "A": [opt(1, "A", *mwf("09:00", "09:50"))],
        "B": [opt(2, "B", *tr("13:00", "14:20")), opt(3, "B", *mwf("10:00", "10:50")), opt(4, "B", *mwf("15:00", "15:50"))],
    }
    result = solve(options)
    assert [s.crns for s in result.schedules][0] == ["1", "3"]  # 3 days, 10-min gaps
    assert result.schedules[0].days_on_campus == 3
    assert result.schedules[0].gap_minutes == 30
    assert result.schedules[-1].days_on_campus == 5


def test_preferences_filter_sections():
    options = {
        "A": [opt(1, "A", *mwf("08:00", "08:50")), opt(2, "A", *tr("12:00", "13:20"))],
    }
    early = solve(options, Preferences(earliest_start=parse_hhmm("09:00")))
    assert [s.crns for s in early.schedules] == [["2"]]

    no_tuesday = solve(options, Preferences(days_off=frozenset({"T"})))
    assert [s.crns for s in no_tuesday.schedules] == [["1"]]


def test_full_sections_excluded_unless_requested():
    options = {"A": [opt(1, "A", *mwf("09:00", "09:50"), full=True)]}
    excluded = solve(options)
    assert excluded.unsatisfiable_courses == ["A"]
    assert solve(options, Preferences(include_full=True)).schedules[0].crns == ["1"]


def test_conflicting_pairs_explains_empty_results():
    options = {
        "A": [opt(1, "A", *mwf("09:00", "09:50"))],
        "B": [opt(2, "B", ("M", "09:30", "10:20"))],
        "C": [opt(3, "C", *tr("09:00", "10:20"))],
    }
    assert solve(options).schedules == []
    assert conflicting_pairs(options) == [("A", "B")]


def test_max_results_truncates_list_but_not_search():
    options = {f"C{i}": [opt(i * 10 + j, f"C{i}", ("M" if j % 2 else "T", f"{8 + i}:00", f"{8 + i}:50")) for j in range(3)]
               for i in range(4)}
    result = solve(options, Preferences(max_results=5))
    assert len(result.schedules) == 5
    assert result.truncated is False


@pytest.mark.parametrize("value,expected", [("00:00", 0), ("09:30", 570), ("23:59", 1439)])
def test_time_parsing(value, expected):
    assert parse_hhmm(value) == expected
    assert format_minutes(expected) == value


@pytest.mark.parametrize("bad", ["24:00", "9", "ab:cd", "12:60"])
def test_time_parsing_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_hhmm(bad)
