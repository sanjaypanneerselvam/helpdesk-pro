"""
PHASE 1 - plain Django views that return JSON, no DRF.

Compare these with tickets/views.py to see how much work DRF saves you.
"""
from django.conf import settings
from django.http import JsonResponse

from .models import Ticket


def ping(request):
    """GET /api/ping/ -> {"status": "ok", "message": "pong"}"""
    return JsonResponse({"status": "ok", "message": "pong"})


def tickets_basic(request):
    """
    GET /api/tickets-basic/  - read-only ticket list, no login, no scoping.

    Teaching view only: because it is open to everyone it answers ONLY while
    DEBUG is True. The real, protected endpoint is /api/v1/tickets/.
    """
    if not settings.DEBUG:
        return JsonResponse({"detail": "Not found."}, status=404)
    rows = list(Ticket.objects.values("id", "title", "status", "priority", "created_at")[:50])
    return JsonResponse({"count": len(rows), "results": rows})
