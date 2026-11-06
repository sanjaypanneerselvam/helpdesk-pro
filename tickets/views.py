from django.db.models import Count, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin, IsAgentOrAdmin, IsCustomerOrAdmin

from .models import Category, Ticket
from .permissions import IsOwnerOrStaff
from .serializers import (
    CategorySerializer,
    CommentSerializer,
    TicketDetailSerializer,
    TicketSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /categories/ - for the dropdown on the Create Ticket screen."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = None


class TicketViewSet(viewsets.ModelViewSet):
    """
    Everything about tickets.

    Standard actions (from ModelViewSet): list, create, retrieve, partial_update, destroy
    Extra actions:  queue, summary, assign, comments
    """

    # PUT is not in the API design, only PATCH.
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "updated_at", "priority", "status"]
    ordering = ["-created_at"]

    # --- Queryset scoping: who can see which tickets ---------------------
    def get_queryset(self):
        user = self.request.user
        qs = Ticket.objects.select_related("category", "created_by", "assigned_to")
        if user.is_admin:
            return qs
        if user.is_agent:
            return qs.filter(Q(assigned_to=user) | Q(assigned_to__isnull=True))
        return qs.filter(created_by=user)  # customer: own tickets only

    # --- Query params: ?status= &priority= &category= &assigned_to=me ----
    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)  # search + ordering
        if self.action in ("list", "queue"):
            p = self.request.query_params
            if p.get("status"):
                queryset = queryset.filter(status=p["status"].upper())
            if p.get("priority"):
                queryset = queryset.filter(priority=p["priority"].upper())
            if p.get("category", "").isdigit():
                queryset = queryset.filter(category_id=int(p["category"]))
            if p.get("assigned_to") == "me":
                queryset = queryset.filter(assigned_to=self.request.user)
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TicketDetailSerializer  # includes nested comments
        return TicketSerializer

    def get_permissions(self):
        if self.action == "create":
            classes = [IsAuthenticated, IsCustomerOrAdmin]
        elif self.action == "destroy":
            classes = [IsAuthenticated, IsAdmin]
        elif self.action in ("queue", "assign"):
            classes = [IsAuthenticated, IsAgentOrAdmin]
        else:
            classes = [IsAuthenticated, IsOwnerOrStaff]
        return [cls() for cls in classes]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    # --- Extra endpoints --------------------------------------------------
    @action(detail=False, methods=["get"])
    def queue(self, request):
        """GET /tickets/queue/ - unassigned OPEN tickets."""
        qs = self.get_queryset().filter(status=Ticket.Status.OPEN, assigned_to__isnull=True)
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """GET /tickets/summary/ - counts by status for the tickets this user can see."""
        rows = self.get_queryset().order_by().values_list("status").annotate(n=Count("id"))
        counts = {s: 0 for s in Ticket.Status.values}
        counts.update(dict(rows))
        counts["total"] = sum(counts.values())
        return Response(counts)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """POST /tickets/{id}/assign/ - assign the ticket to the caller."""
        ticket = self.get_object()
        if ticket.assigned_to_id:
            return Response(
                {"detail": f"Ticket is already assigned to {ticket.assigned_to.username}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if ticket.status == Ticket.Status.CLOSED:
            return Response(
                {"detail": "A closed ticket cannot be assigned."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ticket.assigned_to = request.user
        ticket.save()
        return Response(TicketSerializer(ticket, context={"request": request}).data)

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, pk=None):
        """GET/POST /tickets/{id}/comments/"""
        ticket = self.get_object()  # scoping + object permission => 404 for strangers

        if request.method == "GET":
            visible = ticket.comments_visible_to(request.user)
            return Response(CommentSerializer(visible, many=True).data)

        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get("is_internal") and not request.user.is_support_staff:
            raise PermissionDenied("Customers cannot create internal notes.")
        serializer.save(ticket=ticket, author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class StatsView(APIView):
    """GET /stats/ - admin only. Counts by status and priority."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        by_status = {s: 0 for s in Ticket.Status.values}
        by_priority = {p: 0 for p in Ticket.Priority.values}
        by_status.update(dict(Ticket.objects.order_by().values_list("status").annotate(n=Count("id"))))
        by_priority.update(dict(Ticket.objects.order_by().values_list("priority").annotate(n=Count("id"))))
        return Response(
            {
                "total": sum(by_status.values()),
                "unassigned": Ticket.objects.filter(assigned_to__isnull=True).exclude(
                    status=Ticket.Status.CLOSED
                ).count(),
                "by_status": by_status,
                "by_priority": by_priority,
            }
        )
