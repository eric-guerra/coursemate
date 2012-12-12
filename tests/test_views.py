import json

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def catalog():
    call_command("seed_courses", verbosity=0)


def post(client, payload):
    return client.post("/api/schedules", data=json.dumps(payload), content_type="application/json")


def test_index_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"CourseMate" in response.content


def test_course_search(client):
    data = client.get("/api/courses", {"q": "algor"}).json()
    assert [c["code"] for c in data["results"]] == ["COSC 3320"]
    assert data["results"][0]["sections"] == 2


def test_generate_returns_ranked_schedules(client):
    response = post(client, {"courses": ["cosc 1430", "COSC 3320", "MATH 2318"]})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] > 0
    first = body["schedules"][0]
    assert {s["course"] for s in first["sections"]} == {"COSC 1430", "COSC 3320", "MATH 2318"}
    days = [s["daysOnCampus"] for s in body["schedules"]]
    assert days == sorted(days)


def test_full_sections_are_skipped_by_default(client):
    body = post(client, {"courses": ["COSC 1430"]}).json()
    assert "10002" not in {crn for s in body["schedules"] for crn in s["crns"]}
    body = post(client, {"courses": ["COSC 1430"], "includeFull": True}).json()
    assert "10002" in {crn for s in body["schedules"] for crn in s["crns"]}


def test_days_off_and_time_window(client):
    body = post(client, {"courses": ["COSC 3380"], "daysOff": ["T", "R"]}).json()
    assert [s["crns"] for s in body["schedules"]] == [["10302"]]

    body = post(client, {"courses": ["ENGL 1302"], "latest": "17:00"}).json()
    # 30101 is full and 30102 ends at 17:20, so nothing fits
    assert body["unsatisfiable"] == ["ENGL 1302"]


@pytest.mark.parametrize(
    "payload,message",
    [
        ({}, "courses must be"),
        ({"courses": "COSC 1430"}, "courses must be"),
        ({"courses": ["NOPE 1000"]}, "Unknown course"),
        ({"courses": ["COSC 1430"], "earliest": "9am"}, "HH:MM"),
        ({"courses": [f"X{i}" for i in range(9)]}, "at most"),
    ],
)
def test_validation_errors(client, payload, message):
    response = post(client, payload)
    assert response.status_code == 400
    assert message in response.json()["error"]


def test_rejects_non_json(client):
    response = client.post("/api/schedules", data="nope", content_type="application/json")
    assert response.status_code == 400


def test_seed_is_idempotent():
    from scheduler.models import Meeting, Section

    before = (Section.objects.count(), Meeting.objects.count())
    call_command("seed_courses", verbosity=0)
    assert (Section.objects.count(), Meeting.objects.count()) == before
