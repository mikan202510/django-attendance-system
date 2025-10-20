
# hr_core/models_hr.py
from django.db import models
from django.conf import settings

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

class Position(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

class EmploymentType(models.TextChoices):
    REGULAR  = "REGULAR",  "正社員"
    CONTRACT = "CONTRACT", "契約社員"
    PARTTIME = "PARTTIME", "パート/アルバイト"
    DISPATCH = "DISPATCH", "派遣"
    INTERN   = "INTERN",   "インターン"

class EmployeeProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="employee_profile")
    employee_code = models.CharField(max_length=32, blank=True, default="")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    position   = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True)
    employment_type = models.CharField(max_length=16, choices=EmploymentType.choices,
                                       default=EmploymentType.REGULAR)
    base_hours_per_day = models.FloatField(default=8.0)
    status = models.CharField(max_length=32, default="ACTIVE")
    is_manager = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} ({self.employee_code or '-'})"
