# hrm_py/attendance/serializers.py
from rest_framework import serializers
from .models import Attendance

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ["id", "punch_type", "punched_at", "work_date", "note"]
        read_only_fields = ["id", "punched_at", "work_date"]

