# hr_core/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsHrAdminOrReadOnly(BasePermission):
    """
    GET系は認証ユーザーなら可／書き込みは HR 管理者のみ（is_staff または HR_ADMIN グループ）。
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return bool(user.is_staff or user.groups.filter(name="HR_ADMIN").exists())

class IsHrAdminOrSelf(BasePermission):
    """
    Employee のオブジェクト権限：HR管理者は全件、一般ユーザーは自分の Employee のみ参照可（更新は不可）。
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.groups.filter(name="HR_ADMIN").exists():
            return True
        if request.method in SAFE_METHODS:
            return obj.user_id == user.id
        return False

