# hr_core/views.py
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions, filters
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Department, Position, Employee
from .serializers import (
    DepartmentSerializer,
    PositionSerializer,
    EmployeeReadSerializer,
    EmployeeWriteSerializer,
)
from .permissions import IsHrAdminOrReadOnly, IsHrAdminOrSelf

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsHrAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active", "parent"]
    search_fields = ["name", "code"]
    ordering_fields = ["code", "name"]

class PositionViewSet(viewsets.ModelViewSet):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    permission_classes = [IsHrAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name"]
    ordering_fields = ["rank", "name"]

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related("user", "department", "position").all()
    permission_classes = [IsHrAdminOrSelf]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["employment_type", "status", "department", "position", "is_manager"]
    search_fields = ["employee_code", "user__username", "user__first_name", "user__last_name", "user__email"]
    ordering_fields = ["employee_code", "hire_date", "updated_at"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return EmployeeWriteSerializer
        return EmployeeReadSerializer

class MeEmployeeAPIView(APIView):
    """
    自分の社員情報：GET /api/hr/me
    """
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        try:
            emp = Employee.objects.select_related("user", "department", "position").get(user=request.user)
        except Employee.DoesNotExist:
            return Response({"detail": "Employee record not found for current user."}, status=404)
        return Response(EmployeeReadSerializer(emp).data)
