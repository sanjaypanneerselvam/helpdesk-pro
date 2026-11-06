"""Role based permission classes. A permission class answers: may this user call this endpoint?"""
from rest_framework.permissions import BasePermission


class _RolePermission(BasePermission):
    allowed_roles = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in self.allowed_roles)


class IsAgent(_RolePermission):
    allowed_roles = ("AGENT",)


class IsAdmin(_RolePermission):
    allowed_roles = ("ADMIN",)


class IsAgentOrAdmin(_RolePermission):
    allowed_roles = ("AGENT", "ADMIN")


class IsCustomerOrAdmin(_RolePermission):
    """Agents answer tickets, they don't raise them."""

    allowed_roles = ("CUSTOMER", "ADMIN")
