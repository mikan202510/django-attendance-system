# hr_core/models.py

# --- HR(人事)系モデル ---------------------------------------------------------
from .models_hr import (
    Department,
    Position,
    EmployeeProfile,
)

# 互換エイリアス：既存コードが Employee を参照しても動くように
Employee = EmployeeProfile


# --- 申請(残業/休暇)系モデル ---------------------------------------------------
# ※ 実体は models_requests.py に定義してください
from .models_requests import (
    OvertimeRequest,
    LeaveRequest,
    RequestStatus,
    LeaveType,   # 休暇区分を使う画面がある想定。未使用なら削除可
)


# --- 公開シンボル --------------------------------------------------------------
__all__ = [
    # HR
    "Department",
    "Position",
    "EmployeeProfile",
    "Employee",  # 互換用

    # Requests
    "OvertimeRequest",
    "LeaveRequest",
    "RequestStatus",
    "LeaveType",
]


# --- 起動時の健全性チェック（None混入や未定義の取りこぼし防止） -------------
assert Department and Position and EmployeeProfile, "models_hr の読み込みに失敗しています"
assert OvertimeRequest and LeaveRequest and RequestStatus, "models_requests の読み込みに失敗しています"



