"""
Run with:  python manage.py test

Each test method checks one rule from the permission matrix / API design.
"""
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import User
from tickets.models import Category, Comment, Ticket

BASE = "/api/v1"


class BaseCase(APITestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Account")
        self.ravi = User.objects.create_user("ravi", "ravi@x.com", "Pass@12345")
        self.meera = User.objects.create_user("meera", "meera@x.com", "Pass@12345")
        self.asha = User.objects.create_user("asha", "asha@x.com", "Pass@12345", role="AGENT")
        self.bob = User.objects.create_user("bob", "bob@x.com", "Pass@12345", role="AGENT")
        self.boss = User.objects.create_user("boss", "boss@x.com", "Pass@12345", role="ADMIN")
        self.ticket = Ticket.objects.create(
            title="Cannot log in", description="403", category=self.cat,
            priority="HIGH", created_by=self.ravi,
        )

    def login(self, user):
        self.client.force_authenticate(user)

    def make_ticket(self, **kw):
        data = dict(title="T", description="d", category=self.cat, created_by=self.ravi)
        data.update(kw)
        return Ticket.objects.create(**data)


class Phase1BasicApiTests(BaseCase):
    def test_ping(self):
        r = self.client.get("/api/ping/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["message"], "pong")

    @override_settings(DEBUG=True)
    def test_tickets_basic_returns_json(self):
        r = self.client.get("/api/tickets-basic/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["count"], 1)

    def test_tickets_basic_is_disabled_when_debug_off(self):
        # This open endpoint must never answer in production.
        self.assertEqual(self.client.get("/api/tickets-basic/").status_code, 404)


class AuthTests(BaseCase):
    def test_register_creates_customer_only(self):
        r = self.client.post(f"{BASE}/auth/register/", {
            "username": "new", "email": "n@x.com", "password": "Str0ng!Pass#1",
            "password2": "Str0ng!Pass#1", "role": "ADMIN",  # role must be ignored
        })
        self.assertEqual(r.status_code, 201)
        self.assertEqual(User.objects.get(username="new").role, "CUSTOMER")

    def test_register_password_mismatch(self):
        r = self.client.post(f"{BASE}/auth/register/", {
            "username": "new", "email": "n@x.com", "password": "Str0ng!Pass#1", "password2": "x",
        })
        self.assertEqual(r.status_code, 400)
        self.assertIn("password2", r.json())

    def test_login_returns_token_and_role(self):
        r = self.client.post(f"{BASE}/auth/login/", {"username": "asha", "password": "Pass@12345"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("token", r.json())
        self.assertEqual(r.json()["user"]["role"], "AGENT")

    def test_login_wrong_password(self):
        r = self.client.post(f"{BASE}/auth/login/", {"username": "asha", "password": "nope"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json(), {"detail": "Invalid credentials."})

    def test_token_works_then_logout_kills_it(self):
        token = self.client.post(
            f"{BASE}/auth/login/", {"username": "ravi", "password": "Pass@12345"}
        ).json()["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.get(f"{BASE}/auth/me/").status_code, 200)
        self.assertEqual(self.client.post(f"{BASE}/auth/logout/").status_code, 200)
        self.assertEqual(self.client.get(f"{BASE}/auth/me/").status_code, 401)

    def test_no_token_is_401(self):
        self.assertEqual(self.client.get(f"{BASE}/tickets/").status_code, 401)

    def test_change_password(self):
        self.login(self.ravi)
        bad = self.client.post(f"{BASE}/auth/change-password/",
                               {"old_password": "wrong", "new_password": "Br4nd!New#Pass"})
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post(f"{BASE}/auth/change-password/",
                              {"old_password": "Pass@12345", "new_password": "Br4nd!New#Pass"})
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(User.objects.get(username="ravi").check_password("Br4nd!New#Pass"))

    def test_me_cannot_change_role(self):
        self.login(self.ravi)
        r = self.client.patch(f"{BASE}/auth/me/", {"role": "ADMIN", "phone": "99999"})
        self.assertEqual(r.status_code, 200)
        self.ravi.refresh_from_db()
        self.assertEqual(self.ravi.role, "CUSTOMER")
        self.assertEqual(self.ravi.phone, "99999")


class TicketVisibilityTests(BaseCase):
    """Queryset scoping."""

    def test_customer_sees_only_own(self):
        self.make_ticket(title="Meera's", created_by=self.meera)
        self.login(self.ravi)
        r = self.client.get(f"{BASE}/tickets/")
        self.assertEqual([t["title"] for t in r.json()["results"]], ["Cannot log in"])

    def test_customer_gets_404_for_others_ticket(self):
        self.login(self.meera)
        self.assertEqual(self.client.get(f"{BASE}/tickets/{self.ticket.id}/").status_code, 404)
        self.assertEqual(self.client.patch(f"{BASE}/tickets/{self.ticket.id}/", {"status": "CLOSED"}).status_code, 404)

    def test_agent_sees_unassigned_and_own_but_not_others(self):
        mine = self.make_ticket(title="mine", assigned_to=self.asha)
        theirs = self.make_ticket(title="theirs", assigned_to=self.bob)
        self.login(self.asha)
        ids = {t["id"] for t in self.client.get(f"{BASE}/tickets/").json()["results"]}
        self.assertEqual(ids, {self.ticket.id, mine.id})
        self.assertEqual(self.client.get(f"{BASE}/tickets/{theirs.id}/").status_code, 404)

    def test_admin_sees_all(self):
        self.make_ticket(title="b", assigned_to=self.bob)
        self.login(self.boss)
        self.assertEqual(self.client.get(f"{BASE}/tickets/").json()["count"], 2)


class TicketCreateTests(BaseCase):
    payload = {"title": "Printer", "description": "Broken", "category": 1, "priority": "HIGH"}

    def test_customer_creates_ticket_with_sample_shape(self):
        self.login(self.ravi)
        r = self.client.post(f"{BASE}/tickets/", {**self.payload, "category": self.cat.id, "status": "CLOSED"})
        self.assertEqual(r.status_code, 201)
        body = r.json()
        self.assertEqual(body["status"], "OPEN")  # client cannot choose status
        self.assertEqual(body["created_by"], "ravi")
        self.assertIsNone(body["assigned_to"])
        self.assertEqual(body["category"], {"id": self.cat.id, "name": "Account"})
        self.assertEqual(body["comment_count"], 0)

    def test_agent_cannot_create(self):
        self.login(self.asha)
        r = self.client.post(f"{BASE}/tickets/", {**self.payload, "category": self.cat.id})
        self.assertEqual(r.status_code, 403)

    def test_admin_can_create(self):
        self.login(self.boss)
        r = self.client.post(f"{BASE}/tickets/", {**self.payload, "category": self.cat.id})
        self.assertEqual(r.status_code, 201)

    def test_missing_fields_400(self):
        self.login(self.ravi)
        self.assertEqual(self.client.post(f"{BASE}/tickets/", {"title": "x"}).status_code, 400)


class StatusRuleTests(BaseCase):
    def patch(self, status_value, ticket=None):
        ticket = ticket or self.ticket
        return self.client.patch(f"{BASE}/tickets/{ticket.id}/", {"status": status_value})

    def test_staff_must_move_one_step_at_a_time(self):
        self.login(self.asha)
        self.assertEqual(self.patch("RESOLVED").status_code, 400)  # OPEN -> RESOLVED skips a step
        self.assertEqual(self.patch("IN_PROGRESS").status_code, 200)
        self.assertEqual(self.patch("RESOLVED").status_code, 200)
        self.assertEqual(self.patch("CLOSED").status_code, 200)

    def test_customer_cannot_start_work(self):
        self.login(self.ravi)
        r = self.patch("IN_PROGRESS")
        self.assertEqual(r.status_code, 400)
        self.assertIn("detail", r.json())

    def test_customer_can_close_resolved_and_reopen(self):
        self.ticket.status = "RESOLVED"
        self.ticket.save()
        self.login(self.ravi)
        self.assertEqual(self.patch("CLOSED").status_code, 200)
        self.assertEqual(self.patch("OPEN").status_code, 200)

    def test_customer_cannot_close_open_ticket(self):
        self.login(self.ravi)
        self.assertEqual(self.patch("CLOSED").status_code, 400)

    def test_customer_cannot_edit_other_fields(self):
        self.login(self.ravi)
        r = self.client.patch(f"{BASE}/tickets/{self.ticket.id}/", {"priority": "LOW"})
        self.assertEqual(r.status_code, 403)

    def test_agent_can_change_priority(self):
        self.login(self.asha)
        r = self.client.patch(f"{BASE}/tickets/{self.ticket.id}/", {"priority": "LOW"})
        self.assertEqual(r.status_code, 200)


class QueueAndAssignTests(BaseCase):
    def test_queue_lists_only_unassigned_open(self):
        self.make_ticket(title="taken", assigned_to=self.bob)
        self.make_ticket(title="done", status="RESOLVED")
        self.login(self.asha)
        r = self.client.get(f"{BASE}/tickets/queue/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([t["id"] for t in r.json()["results"]], [self.ticket.id])

    def test_customer_cannot_see_queue(self):
        self.login(self.ravi)
        self.assertEqual(self.client.get(f"{BASE}/tickets/queue/").status_code, 403)

    def test_assign_to_self_once(self):
        self.login(self.asha)
        r = self.client.post(f"{BASE}/tickets/{self.ticket.id}/assign/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["assigned_to"], "asha")
        self.assertEqual(self.client.post(f"{BASE}/tickets/{self.ticket.id}/assign/").status_code, 400)

    def test_customer_cannot_assign(self):
        self.login(self.ravi)
        self.assertEqual(self.client.post(f"{BASE}/tickets/{self.ticket.id}/assign/").status_code, 403)

    def test_assigned_to_me_filter(self):
        self.make_ticket(title="mine", assigned_to=self.asha)
        self.login(self.asha)
        r = self.client.get(f"{BASE}/tickets/?assigned_to=me")
        self.assertEqual([t["title"] for t in r.json()["results"]], ["mine"])


class CommentTests(BaseCase):
    def setUp(self):
        super().setUp()
        Comment.objects.create(ticket=self.ticket, author=self.ravi, message="public")
        Comment.objects.create(ticket=self.ticket, author=self.asha, message="secret", is_internal=True)

    def test_customer_cannot_see_internal_notes(self):
        self.login(self.ravi)
        listing = self.client.get(f"{BASE}/tickets/{self.ticket.id}/comments/").json()
        self.assertEqual([c["message"] for c in listing], ["public"])
        detail = self.client.get(f"{BASE}/tickets/{self.ticket.id}/").json()
        self.assertEqual([c["message"] for c in detail["comments"]], ["public"])
        self.assertEqual(detail["comment_count"], 1)

    def test_agent_sees_internal_notes(self):
        self.login(self.asha)
        detail = self.client.get(f"{BASE}/tickets/{self.ticket.id}/").json()
        self.assertEqual(len(detail["comments"]), 2)
        self.assertEqual(detail["comment_count"], 2)

    def test_customer_cannot_create_internal_note(self):
        self.login(self.ravi)
        r = self.client.post(f"{BASE}/tickets/{self.ticket.id}/comments/",
                             {"message": "hi", "is_internal": True})
        self.assertEqual(r.status_code, 403)

    def test_customer_adds_public_comment(self):
        self.login(self.ravi)
        r = self.client.post(f"{BASE}/tickets/{self.ticket.id}/comments/", {"message": "any news?"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["author"], "ravi")

    def test_stranger_cannot_comment(self):
        self.login(self.meera)
        r = self.client.post(f"{BASE}/tickets/{self.ticket.id}/comments/", {"message": "hi"})
        self.assertEqual(r.status_code, 404)

    def test_blank_comment_rejected(self):
        self.login(self.ravi)
        r = self.client.post(f"{BASE}/tickets/{self.ticket.id}/comments/", {"message": ""})
        self.assertEqual(r.status_code, 400)


class DeleteTests(BaseCase):
    def test_only_admin_can_delete(self):
        url = f"{BASE}/tickets/{self.ticket.id}/"
        self.login(self.ravi)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.login(self.asha)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.login(self.boss)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(Ticket.objects.filter(pk=self.ticket.id).exists())


class UsersAndStatsTests(BaseCase):
    def test_users_admin_only(self):
        for user in (self.ravi, self.asha):
            self.login(user)
            self.assertEqual(self.client.get(f"{BASE}/users/").status_code, 403)
        self.login(self.boss)
        r = self.client.get(f"{BASE}/users/?role=AGENT")
        self.assertEqual({u["username"] for u in r.json()["results"]}, {"asha", "bob"})

    def test_admin_changes_role_and_deactivates(self):
        self.login(self.boss)
        r = self.client.patch(f"{BASE}/users/{self.meera.id}/", {"role": "AGENT", "is_active": False})
        self.assertEqual(r.status_code, 200)
        self.meera.refresh_from_db()
        self.assertEqual((self.meera.role, self.meera.is_active), ("AGENT", False))

    def test_admin_cannot_demote_or_deactivate_self(self):
        self.login(self.boss)
        self.assertEqual(self.client.patch(f"{BASE}/users/{self.boss.id}/", {"is_active": False}).status_code, 400)
        self.assertEqual(self.client.patch(f"{BASE}/users/{self.boss.id}/", {"role": "CUSTOMER"}).status_code, 400)

    def test_stats_admin_only_and_counts(self):
        self.make_ticket(status="RESOLVED", priority="LOW")
        self.login(self.asha)
        self.assertEqual(self.client.get(f"{BASE}/stats/").status_code, 403)
        self.login(self.boss)
        r = self.client.get(f"{BASE}/stats/").json()
        self.assertEqual(r["total"], 2)
        self.assertEqual(r["by_status"]["OPEN"], 1)
        self.assertEqual(r["by_status"]["RESOLVED"], 1)
        self.assertEqual(r["by_priority"]["HIGH"], 1)

    def test_categories_list_for_logged_in(self):
        self.assertEqual(self.client.get(f"{BASE}/categories/").status_code, 401)
        self.login(self.ravi)
        self.assertEqual(self.client.get(f"{BASE}/categories/").json(), [{"id": self.cat.id, "name": "Account"}])


class QueryParamTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.make_ticket(title="Password reset", priority="LOW", status="RESOLVED")
        self.make_ticket(title="Billing question", priority="HIGH")

    def titles(self, query):
        self.login(self.ravi)
        return [t["title"] for t in self.client.get(f"{BASE}/tickets/{query}").json()["results"]]

    def test_status_filter(self):
        self.assertEqual(self.titles("?status=RESOLVED"), ["Password reset"])

    def test_priority_filter(self):
        self.assertEqual(sorted(self.titles("?priority=HIGH")), ["Billing question", "Cannot log in"])

    def test_search(self):
        self.assertEqual(self.titles("?search=billing"), ["Billing question"])

    def test_ordering(self):
        self.assertEqual(self.titles("?ordering=created_at")[0], "Cannot log in")
        self.assertEqual(self.titles("?ordering=-created_at")[0], "Billing question")

    def test_pagination(self):
        self.login(self.ravi)
        r = self.client.get(f"{BASE}/tickets/?page_size=2").json()
        self.assertEqual((r["count"], len(r["results"])), (3, 2))
        self.assertIsNotNone(r["next"])
        self.assertEqual(len(self.client.get(f"{BASE}/tickets/?page_size=2&page=2").json()["results"]), 1)


class ErrorShapeTests(BaseCase):
    def test_404_does_not_leak_details(self):
        self.login(self.meera)  # not the owner
        other = self.client.get(f"{BASE}/tickets/{self.ticket.id}/")
        missing = self.client.get(f"{BASE}/tickets/9999/")
        self.assertEqual(other.json(), {"detail": "Not found."})
        self.assertEqual(other.json(), missing.json())  # same answer: ticket existence isn't revealed

    def test_permission_error_shape(self):
        self.login(self.ravi)
        r = self.client.get(f"{BASE}/users/")
        self.assertEqual(r.json(), {"detail": "You do not have permission to perform this action."})


class WebScreenTests(BaseCase):
    def test_all_screens_render(self):
        for url in ["/login/", "/register/", "/customer/", "/tickets/", "/tickets/new/",
                    "/tickets/1/", "/agent/queue/", "/profile/", "/admin-panel/", "/admin-panel/users/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
