
# hr_core/views_requests.py
from rest_framework import viewsets, permissions, decorators, response, status
from django.utils import timezone
from .models import OvertimeRequest, LeaveRequest, RequestStatus
from .serializers import OvertimeRequestSerializer, LeaveRequestSerializer

class IsAdminOrOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        return obj.user_id == request.user.id

class OvertimeRequestViewSet(viewsets.ModelViewSet):
    queryset = OvertimeRequest.objects.select_related("user", "approver").order_by("-created_at")
    serializer_class = OvertimeRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrOwner]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()
        me = self.request.query_params.get("me")
        status_param = self.request.query_params.get("status")
        if me == "1":
            qs = qs.filter(user=self.request.user)
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    @decorators.action(methods=["post"], detail=True, permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        obj = self.get_object()
        obj.status = RequestStatus.APPROVED
        obj.approver = request.user
        obj.decided_at = timezone.now()
        obj.save()
        return response.Response(self.get_serializer(obj).data)

    @decorators.action(methods=["post"], detail=True, permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        obj = self.get_object()
        obj.status = RequestStatus.REJECTED
        obj.approver = request.user
        obj.decided_at = timezone.now()
        obj.save()
        return response.Response(self.get_serializer(obj).data)

    @decorators.action(methods=["post"], detail=True)
    def cancel(self, request, pk=None):
        # 本人（所有者）なら取消可
        obj = self.get_object()
        if obj.user != request.user and not request.user.is_staff:
            return response.Response({"detail": "取消権限がありません"}, status=status.HTTP_403_FORBIDDEN)
        obj.status = RequestStatus.CANCELED
        obj.save()
        return response.Response(self.get_serializer(obj).data)


class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.select_related("user", "approver").order_by("-created_at")
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrOwner]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()
        me = self.request.query_params.get("me")
        status_param = self.request.query_params.get("status")
        if me == "1":
            qs = qs.filter(user=self.request.user)
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    @decorators.action(methods=["post"], detail=True, permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        obj = self.get_object()
        obj.status = RequestStatus.APPROVED
        obj.approver = request.user
        obj.decided_at = timezone.now()
        obj.save()
        return response.Response(self.get_serializer(obj).data)

    @decorators.action(methods=["post"], detail=True, permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        obj = self.get_object()
        obj.status = RequestStatus.REJECTED
        obj.approver = request.user
        obj.decided_at = timezone.now()
        obj.save()
        return response.Response(self.get_serializer(obj).data)

    @decorators.action(methods=["post"], detail=True)
    def cancel(self, request, pk=None):
        obj = self.get_object()
        if obj.user != request.user and not request.user.is_staff:
            return response.Response({"detail": "取消権限がありません"}, status=status.HTTP_403_FORBIDDEN)
        obj.status = RequestStatus.CANCELED
        obj.save()
        return response.Response(self.get_serializer(obj).data)
