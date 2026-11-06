from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class HelpDeskUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("HelpDesk", {"fields": ("role", "phone")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("HelpDesk", {"fields": ("email", "role", "phone")}),
    )
