# hr_core/serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers

# モデルは「入口」経由で集約読み込み（models.py で再公開されている前提）
from .models import (
    Department,
    Position,
    Employee,          # = EmployeeProfile のエイリアス（models.pyで定義）
    OvertimeRequest,   # start_datetime / end_datetime を使用
    LeaveRequest,      # date_from / date_to を使用
)


# --- User (Slim) -------------------------------------------------------------
class UserSlimSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        # 必要最小限。プロジェクトに合わせて増減OK
        fields = ("id", "username", "first_name", "last_name", "email")


# --- HR: Department / Position ----------------------------------------------
class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = "__all__"


# --- Employee (Read/Write) ---------------------------------------------------
# 既存コードとの互換のためクラス名は維持
class EmployeeReadSerializer(serializers.ModelSerializer):
    # ネストを薄くしたい場合は以下をコメントアウト
    # user = UserSlimSerializer(read_only=True)

    class Meta:
        model = Employee
        fields = "__all__"
        # もし created_at / updated_at が無ければ read_only_fields は指定しないこと


class EmployeeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = "__all__"


# --- Requests: Overtime / Leave ---------------------------------------------
class OvertimeRequestSerializer(serializers.ModelSerializer):
    """
    残業申請:
      - 旧: date + start_time / end_time
      - 新: start_datetime / end_datetime
    """
    class Meta:
        model = OvertimeRequest
        fields = "__all__"


class LeaveRequestSerializer(serializers.ModelSerializer):
    """
    休暇申請:
      - 旧: start_date / end_date
      - 新: date_to / date_from
    """
    class Meta:
        model = LeaveRequest
        fields = "__all__"


