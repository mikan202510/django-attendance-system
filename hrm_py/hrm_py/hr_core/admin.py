# hr_core/admin.py
from django.contrib import admin
from .models import Department, Position, Employee as EmployeeModel

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

@admin.register(EmployeeModel)
class EmployeeAdmin(admin.ModelAdmin):
    # EmployeeProfile のフィールドが未確定でも安全に動く最小構成
    list_display = ("id",)

