# hr_core/models_requests.py
from django.conf import settings
from django.db import models


class RequestStatus(models.TextChoices):
    PENDING = "PENDING", "申請中"
    APPROVED = "APPROVED", "承認"
    REJECTED = "REJECTED", "却下"
    CANCELED = "CANCELED", "取消"


class OvertimeRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="overtime_requests")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="overtime_approvals")
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hr_core_overtime_request"
        ordering = ("-created_at",)

    def __str__(self):
        return f"[{self.get_status_display()}] {self.user} {self.start_datetime:%Y-%m-%d %H:%M}→{self.end_datetime:%H:%M}"


class LeaveType(models.TextChoices):
    ANNUAL = "ANNUAL", "年休"
    SICK = "SICK", "病欠"
    OTHER = "OTHER", "その他"


class LeaveRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leave_requests")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="leave_approvals")
    date_from = models.DateField()
    date_to = models.DateField()
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices, default=LeaveType.ANNUAL)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hr_core_leave_request"
        ordering = ("-created_at",)

    def __str__(self):
        return f"[{self.get_status_display()}] {self.user} {self.date_from:%Y-%m-%d}〜{self.date_to:%Y-%m-%d}"

