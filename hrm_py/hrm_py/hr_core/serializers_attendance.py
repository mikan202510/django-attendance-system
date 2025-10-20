# hr_core/serializers_attendance.py
from rest_framework import serializers
from .models_attendance import AttendancePunch, PunchType

class AttendancePunchSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendancePunch
        fields = ["id", "punched_at", "punch_type", "note"]

class PunchCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[c[0] for c in PunchType.choices])
    note = serializers.CharField(required=False, allow_blank=True, default="")
    # 任意: クライアントからサーバ時刻ではなく任意時刻を送るとき
    punched_at = serializers.DateTimeField(required=False)
