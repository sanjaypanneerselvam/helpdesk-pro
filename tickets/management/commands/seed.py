"""python manage.py seed  - creates demo categories, users and tickets (safe to run twice)."""
from django.core.management.base import BaseCommand

from accounts.models import User
from tickets.models import Category, Comment, Ticket

PASSWORD = "Pass@12345"

USERS = [
    # username, email, role
    ("ravi", "ravi@example.com", "CUSTOMER"),
    ("meera", "meera@example.com", "CUSTOMER"),
    ("asha", "asha@example.com", "AGENT"),
    ("admin", "admin@example.com", "ADMIN"),
]

CATEGORIES = ["Account", "Billing", "Technical", "General"]

# title, description, category, priority, status, created_by, assigned_to
TICKETS = [
    ("Cannot log in", "Error 403 after password reset", "Account", "HIGH", "OPEN", "ravi", None),
    ("Invoice shows wrong amount", "March invoice is charged twice", "Billing", "MEDIUM", "IN_PROGRESS", "ravi", "asha"),
    ("App crashes on upload", "Crashes when I upload a PDF over 10 MB", "Technical", "URGENT", "OPEN", "meera", None),
    ("Change my email address", "Please update my email on file", "Account", "LOW", "RESOLVED", "ravi", "asha"),
    ("How do I export data?", "Is there a CSV export?", "General", "LOW", "CLOSED", "meera", "asha"),
]


class Command(BaseCommand):
    help = "Create demo data"

    def handle(self, *args, **options):
        for name in CATEGORIES:
            Category.objects.get_or_create(name=name)

        users = {}
        for username, email, role in USERS:
            user, created = User.objects.get_or_create(
                username=username, defaults={"email": email, "role": role}
            )
            if created:
                user.set_password(PASSWORD)
                if role == "ADMIN":
                    user.is_staff = True  # lets "admin" log in to /admin/ too
                    user.is_superuser = True
                user.save()
            users[username] = user

        for title, desc, cat, prio, st, creator, agent in TICKETS:
            ticket, created = Ticket.objects.get_or_create(
                title=title,
                defaults={
                    "description": desc,
                    "category": Category.objects.get(name=cat),
                    "priority": prio,
                    "status": st,
                    "created_by": users[creator],
                    "assigned_to": users[agent] if agent else None,
                },
            )
            if created and agent:
                Comment.objects.create(ticket=ticket, author=users[agent], message="Looking into this now.")
                Comment.objects.create(
                    ticket=ticket, author=users[agent], message="Customer seems to be on an old version.",
                    is_internal=True,
                )

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write(f"Users (password for all: {PASSWORD}):")
        for username, _, role in USERS:
            self.stdout.write(f"  {username:<6} {role}")
