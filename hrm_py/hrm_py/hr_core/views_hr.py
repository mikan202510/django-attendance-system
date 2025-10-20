# hr_core/views_hr.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from .models_hr import EmployeeProfile
from .serializers_hr import HRMeSerializer

class HRMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            ep = (EmployeeProfile.objects
                  .select_related("user", "department", "position")
                  .get(user=request.user))
        except EmployeeProfile.DoesNotExist:
            # プロファイル未作成でも200で空を返す（Streamlit側は警告文を表示する仕様）
            return Response({}, status=status.HTTP_200_OK)
        return Response(HRMeSerializer(ep).data, status=status.HTTP_200_OK)

