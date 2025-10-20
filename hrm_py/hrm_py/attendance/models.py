# hrm_py/attendance/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

class Attendance(models.Model):
    class PunchType(models.TextChoices):
        IN = "IN", "出勤"
        OUT = "OUT", "退勤"
        BREAK_START = "BREAK_START", "休憩開始"
        BREAK_END = "BREAK_END", "休憩終了"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    punch_type = models.CharField(max_length=12, choices=PunchType.choices)
    punched_at = models.DateTimeField(default=timezone.now)  # 保存はUTC、表示はJST
    work_date = models.DateField(blank=True)                 # 集計用の日付（JST基準）
    note = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        # work_date が未設定なら、JSTのカレンダー日付で自動設定
        if not self.work_date:
            local_dt = timezone.localtime(self.punched_at, JST)
            self.work_date = local_dt.date()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} {self.work_date} {self.punch_type}"

