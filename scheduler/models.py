from django.core.exceptions import ValidationError
from django.db import models

from .solver import SectionOption, TimeSlot


class Course(models.Model):
    code = models.CharField(max_length=16, unique=True)        # e.g. COSC 3320
    title = models.CharField(max_length=200)
    department = models.CharField(max_length=8, db_index=True)
    credits = models.PositiveSmallIntegerField(default=3)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} {self.title}"


class Section(models.Model):
    course = models.ForeignKey(Course, related_name="sections", on_delete=models.CASCADE)
    crn = models.CharField("CRN", max_length=8, unique=True)
    instructor = models.CharField(max_length=120, blank=True)
    capacity = models.PositiveIntegerField(default=40)
    enrolled = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["course__code", "crn"]

    def __str__(self) -> str:
        return f"{self.course.code} ({self.crn})"

    @property
    def is_full(self) -> bool:
        return self.enrolled >= self.capacity

    def to_option(self) -> SectionOption:
        return SectionOption(
            section_id=self.pk,
            course_code=self.course.code,
            crn=self.crn,
            slots=tuple(m.to_slot() for m in self.meetings.all()),
            is_full=self.is_full,
        )


class Meeting(models.Model):
    DAY_CHOICES = [("M", "Mon"), ("T", "Tue"), ("W", "Wed"), ("R", "Thu"), ("F", "Fri")]

    section = models.ForeignKey(Section, related_name="meetings", on_delete=models.CASCADE)
    day = models.CharField(max_length=1, choices=DAY_CHOICES)
    start = models.TimeField()
    end = models.TimeField()
    location = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["day", "start"]

    def clean(self) -> None:
        if self.start >= self.end:
            raise ValidationError("Meeting must end after it starts.")

    def to_slot(self) -> TimeSlot:
        return TimeSlot(
            day=self.day,
            start=self.start.hour * 60 + self.start.minute,
            end=self.end.hour * 60 + self.end.minute,
        )
