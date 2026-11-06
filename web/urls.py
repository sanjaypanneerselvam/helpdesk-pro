from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("", RedirectView.as_view(url="/login/", permanent=False)),
    path("login/", views.login, name="login-page"),                          # S1
    path("register/", views.register, name="register-page"),                 # S2
    path("customer/", views.customer_dashboard, name="customer-dashboard"),  # S3
    path("tickets/", views.ticket_list, name="ticket-list"),                 # S4
    path("tickets/new/", views.ticket_create, name="ticket-create"),         # S5
    path("tickets/<int:ticket_id>/", views.ticket_detail, name="ticket-detail"),  # S6
    path("agent/queue/", views.agent_queue, name="agent-queue"),             # S7
    path("profile/", views.profile, name="profile"),                         # S8
    path("admin-panel/", views.admin_dashboard, name="admin-dashboard"),     # S9
    path("admin-panel/users/", views.admin_users, name="admin-users"),       # S10
]
