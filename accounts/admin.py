from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class DataDictUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Plan", {"fields": ("plan", "stripe_customer_id")}),
    )
    list_display = ("username", "email", "plan", "is_staff")
    list_filter = UserAdmin.list_filter + ("plan",)
