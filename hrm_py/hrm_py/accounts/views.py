# hrm_py/accounts/views.py
from django.contrib.auth.models import User
from rest_framework import serializers, viewsets, permissions

# ユーザー一覧を返す（管理者用APIの例）
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "is_staff"]

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
