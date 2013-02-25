# CourseMate Scheduler

Pick the courses you need and CourseMate generates every **conflict-free weekly schedule**, ranked by fewest days on campus and least idle time between classes. Built with **Django, PostgreSQL/SQLite and jQuery**.

> Portfolio reference implementation of a 2011 university project, built using that era's stack with current Django.

## Features

- Course search API (code or title) with section counts
- Backtracking solver ([scheduler/solver.py](scheduler/solver.py)), pure Python with no Django dependency:
  - Most-constrained-course-first ordering for early pruning
  - Hard constraints: no overlapping meetings, earliest start, latest end, days off, optional full (waitlist) sections
  - Ranking: days on campus, then minutes of gaps
  - A search-node cap protects workers from pathological requests
  - When nothing fits, the response explains why: which courses have no acceptable section, or which pairs always clash
- jQuery week-view calendar with prev/next and arrow-key navigation
- Django admin with inline sections and meetings, and an idempotent `seed_courses` command

## Run

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_courses
python manage.py runserver      # http://localhost:8000
```

Set `DATABASE_NAME` (plus `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`) to use PostgreSQL.

## API

`POST /api/schedules`

```json
{ "courses": ["COSC 1430", "COSC 3320", "MATH 2318"],
  "earliest": "09:00", "latest": "17:00", "daysOff": ["F"], "includeFull": false, "limit": 20 }
```

Returns `schedules[]` (sections, meetings, `daysOnCampus`, `gapMinutes`), plus `unsatisfiable`, `conflicts`, `explored` and `truncated`.

## Test

```bash
pytest     # 26 tests: solver unit tests + API tests against the seeded catalog
```
