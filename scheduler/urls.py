from django.urls import path

from . import views

app_name = "scheduler"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/courses", views.course_search, name="course-search"),
    path("api/schedules", views.generate_schedules, name="generate"),
]
