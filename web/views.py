"""
The HTML screens. These views only render templates: all data is loaded by
JavaScript calling the REST API (see static/web/js/app.js).
"""
from django.shortcuts import render


def page(template, title):
    def view(request, **kwargs):
        return render(request, f"web/{template}.html", {"title": title, **kwargs})

    return view


login = page("login", "Sign in")                              # S1
register = page("register", "Create account")                 # S2
customer_dashboard = page("customer_dashboard", "Dashboard")  # S3
ticket_list = page("ticket_list", "Tickets")                  # S4
ticket_create = page("ticket_create", "New ticket")           # S5
ticket_detail = page("ticket_detail", "Ticket")               # S6 (gets ticket_id from URL)
agent_queue = page("agent_queue", "Agent queue")              # S7
profile = page("profile", "Profile")                          # S8
admin_dashboard = page("admin_dashboard", "Admin dashboard")  # S9
admin_users = page("admin_users", "Users")                    # S10
