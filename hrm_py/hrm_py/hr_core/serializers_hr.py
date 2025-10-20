# hr_core/serializers_hr.py
from rest_framework import serializers
from .models_hr import EmployeeProfile, Department, Position

class DeptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name"]

class PosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["id", "name"]

class HRMeSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    department = DeptSerializer()
    position = PosSerializer()

    class Meta:
        model = EmployeeProfile
        fields = [
            "user", "employee_code", "department", "position",
            "employment_type", "base_hours_per_day", "status", "is_manager"
        ]

    def get_user(self, obj):
        u = obj.user
        return {
            "id": u.id,
            "username": u.username,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
        }
