# attendance/urls.py
from django.urls import path
from .views import PunchAPIView, MyAttendanceAPIView, SummaryAPIView

urlpatterns = [
    path("punch", PunchAPIView.as_view(), name="attendance-punch"),
    path("my", MyAttendanceAPIView.as_view(), name="attendance-my"),
    path("summary", SummaryAPIView.as_view(), name="attendance-summary"),
]

