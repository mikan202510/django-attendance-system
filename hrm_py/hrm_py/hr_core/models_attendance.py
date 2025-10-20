# hr_core/models_attendance.py
from django.conf import settings
from django.db import models
from django.utils import timezone

class PunchType(models.TextChoices):
    IN = "IN", "出勤"
    OUT = "OUT", "退勤"
    BREAK_START = "BREAK_START", "休憩開始"
    BREAK_END   = "BREAK_END", "休憩終了"

class AttendancePunch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance_punches")
    punched_at = models.DateTimeField(default=timezone.now, db_index=True)
    punch_type = models.CharField(max_length=16, choices=PunchType.choices)
    note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["user", "punched_at"]),
        ]
        ordering = ["punched_at"]

    def __str__(self):
        return f"{self.user_id} {self.punch_type} {self.punched_at.isoformat()}"
