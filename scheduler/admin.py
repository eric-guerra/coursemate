from django.contrib import admin

from .models import Course, Meeting, Section


class MeetingInline(admin.TabularInline):
    model = Meeting
    extra = 1


class SectionInline(admin.TabularInline):
    model = Section
    extra = 0
    show_change_link = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "department", "credits")
    list_filter = ("department",)
    search_fields = ("code", "title")
    inlines = [SectionInline]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("crn", "course", "instructor", "enrolled", "capacity")
    search_fields = ("crn", "course__code", "instructor")
    inlines = [MeetingInline]
