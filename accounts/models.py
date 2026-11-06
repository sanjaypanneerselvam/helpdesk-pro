from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Django's normal user + a role and an optional phone number."""

    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        AGENT = "AGENT", "Agent"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CUSTOMER)
    phone = models.CharField(max_length=20, blank=True)

    # Small helpers so the rest of the code reads like English.
    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER

    @property
    def is_agent(self):
        return self.role == self.Role.AGENT

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_support_staff(self):
        """Agent or Admin."""
        return self.role in (self.Role.AGENT, self.Role.ADMIN)

    def save(self, *args, **kwargs):
        # `createsuperuser` should produce an ADMIN, not a CUSTOMER.
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)
