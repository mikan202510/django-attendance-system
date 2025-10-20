# hrm_py/hrm_py/urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# ==============================
# 🔹 URLルーティング設定
# ==============================
urlpatterns = [
    # 管理画面
    path("admin/", admin.site.urls),

    # hr_coreアプリ（勤怠・申請など）のAPI
    path("api/", include("hr_core.urls")),
    path("api-auth/", include("rest_framework.urls")), 
    # JWTトークン認証用エンドポイント
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

# ==============================
# 🔹 管理画面カスタマイズ
# ==============================
admin.site.site_header = "HRMシステム 管理画面"
admin.site.site_title = "HRM管理"
admin.site.index_title = "ようこそ 管理ダッシュボードへ"
