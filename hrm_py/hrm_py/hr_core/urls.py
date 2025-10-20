# hr_core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_hr import HRMeView 

# --- 既存の申請関連 ---
from .views_requests import OvertimeRequestViewSet, LeaveRequestViewSet

# --- 勤怠関連（今回追加した本実装） ---
from .views_attendance import AttendancePunchAPI, AttendanceMyAPI, AttendanceSummaryAPI

# --- ルーター設定 ---
router = DefaultRouter()
router.register(r"requests/overtime", OvertimeRequestViewSet, basename="overtime-request")
router.register(r"requests/leave", LeaveRequestViewSet, basename="leave-request")

# --- URLパターン定義 ---
urlpatterns = [
    # 申請API（ViewSetで自動生成）
    path("", include(router.urls)),

    # 勤怠API（個別APIView）
    path("attendance/punch", AttendancePunchAPI.as_view(), name="attendance-punch"),
    path("attendance/my", AttendanceMyAPI.as_view(), name="attendance-my"),
    path("attendance/summary", AttendanceSummaryAPI.as_view(), name="attendance-summary"),
    path("hr/me", HRMeView.as_view(), name="hr-me"), 
]

