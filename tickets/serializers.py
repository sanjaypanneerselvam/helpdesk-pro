from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from .models import Category, Comment, Ticket

Status = Ticket.Status

# Who may move a ticket from one status to another.
# Staff: OPEN -> IN_PROGRESS -> RESOLVED -> CLOSED (one step at a time), plus reopen.
STAFF_TRANSITIONS = {
    Status.OPEN: {Status.IN_PROGRESS},
    Status.IN_PROGRESS: {Status.RESOLVED},
    Status.RESOLVED: {Status.CLOSED, Status.OPEN},
    Status.CLOSED: {Status.OPEN},
}
# Customers: only RESOLVED -> CLOSED, or reopen to OPEN.
CUSTOMER_TRANSITIONS = {
    Status.RESOLVED: {Status.CLOSED, Status.OPEN},
    Status.CLOSED: {Status.OPEN},
}


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", read_only=True)
    author_role = serializers.CharField(source="author.role", read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "author_role", "message", "is_internal", "created_at"]
        read_only_fields = ["id", "created_at"]


class TicketSerializer(serializers.ModelSerializer):
    # Input: "category": 2        Output: "category": {"id": 2, "name": "Account"}
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    created_by = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id", "title", "description", "category", "priority", "status",
            "created_by", "assigned_to", "comment_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    # --- SerializerMethodField helpers -----------------------------------
    def get_created_by(self, obj):
        return obj.created_by.username

    def get_assigned_to(self, obj):
        return obj.assigned_to.username if obj.assigned_to else None

    def get_comment_count(self, obj):
        return obj.comments_visible_to(self.context["request"].user).count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["category"] = CategorySerializer(instance.category).data
        return data

    # --- Validation (status rules live here) -----------------------------
    def validate(self, attrs):
        user = self.context["request"].user

        # New ticket: always starts OPEN, whatever the client sends.
        if self.instance is None:
            attrs.pop("status", None)
            return attrs

        if user.is_customer:
            forbidden = set(attrs) - {"status"}
            if forbidden:
                raise PermissionDenied("Customers can only close or reopen their tickets.")
            transitions = CUSTOMER_TRANSITIONS
        else:
            transitions = STAFF_TRANSITIONS

        new_status = attrs.get("status")
        old_status = self.instance.status
        if new_status and new_status != old_status:
            if new_status not in transitions.get(old_status, set()):
                raise serializers.ValidationError(
                    f"You cannot change status from {old_status} to {new_status}."
                )
        return attrs


class TicketDetailSerializer(TicketSerializer):
    """Single ticket: same fields plus the nested comments (internal ones only for staff)."""

    comments = serializers.SerializerMethodField()

    class Meta(TicketSerializer.Meta):
        fields = TicketSerializer.Meta.fields + ["comments"]

    def get_comments(self, obj):
        visible = obj.comments_visible_to(self.context["request"].user)
        return CommentSerializer(visible, many=True).data
