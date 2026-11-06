from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import UserViewSet
from tickets.basic_views import ping, tickets_basic
from tickets.views import CategoryViewSet, StatsView, TicketViewSet

# The router builds the list/detail URLs for each ViewSet automatically.
router = DefaultRouter()
router.register("tickets", TicketViewSet, basename="ticket")
router.register("users", UserViewSet, basename="user")
router.register("categories", CategoryViewSet, basename="category")

urlpatterns = [
    path("admin/", admin.site.urls),
    # Phase 1: plain Django JSON views (no DRF)
    path("api/ping/", ping),
    path("api/tickets-basic/", tickets_basic),
    # Phase 2+: the real API
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/stats/", StatsView.as_view(), name="stats"),
    path("api/v1/", include(router.urls)),
    # Login/logout links for the browsable API
    path("api-auth/", include("rest_framework.urls")),
    # HTML screens
    path("", include("web.urls")),
]
