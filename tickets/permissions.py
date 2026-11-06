from rest_framework.permissions import BasePermission


class IsOwnerOrStaff(BasePermission):
    """
    Object-level permission: called after the ticket is loaded.
    The ticket creator, or any agent/admin, may touch it.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_support_staff:
            return True
        return obj.created_by_id == user.id
