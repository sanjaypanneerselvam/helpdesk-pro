# HelpDesk Pro explained for someone new to Django

## 1. The 60-second idea

A **web server** receives an **HTTP request** (a verb like GET/POST + a URL + optional JSON) and sends back a **response** (a status code + JSON or HTML).
Django is a Python framework that does that plumbing. This project has two layers:

```
Browser screens (HTML + a little JS)   ─┐
Postman                                 ─┴──►  REST API  /api/v1/...   ──►  Database (SQLite)
```

The screens contain **no data**. Each page loads, then JavaScript calls the API (`fetch`) and fills the page in.
That is why the task says "test the API in Postman first, then consume it from the screens": both use the same API.

## 2. What happens when you click something

Example: a customer opens a ticket → `GET /api/v1/tickets/14/`

```
 request ──► config/urls.py            "which view handles this URL?"   (router → TicketViewSet)
         ──► authentication            reads "Authorization: Bearer <token>", finds the user   (accounts/authentication.py)
         ──► permissions               "may this role do this action?"                          (accounts/permissions.py, tickets/permissions.py)
         ──► get_queryset()            "which tickets may this user see?"  (customer → only own) (tickets/views.py)
         ──► serializer                turns the Ticket object into JSON                        (tickets/serializers.py)
 response ◄── {"id": 14, "title": ..., "comments": [...]}
```

If the ticket belongs to someone else, `get_queryset()` never returns it → **404**. No token → **401**. Wrong role → **403**.

## 3. File map (where to look)

| File | What it is | Task topic it demonstrates |
|---|---|---|
| `config/settings.py` | Global settings (apps, database, DRF config) | – |
| `config/urls.py` | The URL table | Endpoints |
| `tickets/basic_views.py` | `ping` and `tickets_basic` using plain `JsonResponse` | **API with Django (Phase 1)** |
| `accounts/models.py` | `User` with `role`, `phone` | Data models |
| `tickets/models.py` | `Category`, `Ticket`, `Comment` | Data models |
| `tickets/serializers.py` | Model ⇄ JSON, **status rules in `validate()`**, nested comments, `SerializerMethodField` | **Views and Serializers** |
| `tickets/views.py` | `TicketViewSet`, extra actions `queue`/`assign`/`comments`/`summary`, `StatsView` | **Views (APIView → ViewSet)** |
| `accounts/views.py` | register / login / logout / me / change-password / users | **Authentication** |
| `accounts/permissions.py`, `tickets/permissions.py` | `IsAgent`, `IsAdmin`, `IsOwnerOrStaff` … | **Permissions** |
| `postman/*.json` | Collection + environment | **Postman and project update** |
| `web/templates/web/*.html`, `web/static/web/js/app.js` | Screens S1–S10 | consuming the API |
| `tickets/tests.py` | 50 automated tests | – |
| `CHANGELOG.md` | Bugs found and fixes | "update the project after every Postman finding" |

## 4. The key Django / DRF ideas, one by one

**Model** – a Python class = a database table. `Ticket` has `title`, `status`, `created_by`…
After changing models: `python manage.py makemigrations` (writes a migration file) then `python manage.py migrate` (applies it).

**View** – a function/class that receives a request and returns a response.
 Phase 1 used a plain function: `JsonResponse({"status": "ok"})` (`tickets/basic_views.py`).

**Serializer** – converts model objects to JSON and **validates incoming JSON**.
 `ModelSerializer` writes the fields for you. `SerializerMethodField` is a read-only field computed by a `get_<name>` method (e.g. `comment_count`).

**The three levels of DRF views** (the task asks you to know the progression):
1. `APIView` – you write `get()` / `post()` yourself (see `LoginView`, `StatsView`).
2. Generic views – `CreateAPIView`, `RetrieveUpdateAPIView`… do the common work (see `RegisterView`, `MeView`).
3. `ViewSet` + router – one class gives list/create/retrieve/update/delete and the router creates the URLs (see `TicketViewSet`).

**Authentication = "who are you?"** Login returns a token; the client sends it in every request (`Authorization: Bearer <token>`). The server is **stateless** – it keeps no session per request, it just looks the token up.

**Permissions = "are you allowed?"** `has_permission` runs first (role check); `has_object_permission` runs after the object is loaded (is it your ticket?).

**Queryset scoping** – the most important security rule here: filter in `get_queryset()` so users cannot even *find* what they must not see.

**Status codes you must know**: 200 OK · 201 Created · 204 No Content (delete) · 400 Bad Request (invalid data) · 401 Unauthorized (no/invalid token) · 403 Forbidden (logged in but not allowed) · 404 Not Found.

## 5. Five-minute demo script for your manager

1. `python manage.py runserver`, open `/api/ping/` → JSON. "Phase 1, plain Django."
2. Open `/api/v1/` → browsable API (log in as `admin`). "Phase 2, DRF."
3. Postman: run *Login – customer*, show the token saved by the Tests script. Then *Get ticket – another customer gets 404*.
4. Postman: *Run collection* → all green. "Every endpoint tested for success, 401 and wrong role."
5. Browser: log in as `ravi` → create a ticket → comment. Log out, log in as `asha` → assign it → add an **internal note** → mark resolved. Log in as `ravi` again → the internal note is invisible; close the ticket.
6. Log in as `admin` → stats and user management.
7. Terminal: `python manage.py test` → OK.

## 6. Questions you may be asked

- **Why is a stranger's ticket a 404 and not 403?** Scoping removes it from the queryset; 404 also doesn't reveal that the ticket exists.
- **Where are the status rules enforced?** `TicketSerializer.validate()` in `tickets/serializers.py` (tables `STAFF_TRANSITIONS` / `CUSTOMER_TRANSITIONS`).
- **Can a customer make themselves admin?** No. Register always creates a CUSTOMER and ignores a `role` in the body; `/auth/me/` has `role` read-only; only `/users/{id}/` (admin only) can change it.
- **How are internal notes hidden?** `Ticket.comments_visible_to(user)` filters them out for customers, and it is used by the comments list, the nested comments *and* `comment_count`.
- **What is a migration?** A versioned description of database changes generated from your models.
- **Why `AbstractUser`?** To add `role`/`phone` while keeping Django's login, password hashing and admin. It must be chosen before the first `migrate`.
- **Why a token and not sessions?** Stateless API calls from Postman/JS; sessions are still enabled for the browsable API.
- **Is the token in `localStorage` safe?** It is simple and standard for this kind of project, but JavaScript can read it, so a real product would add HTTPS, token expiry (or JWT refresh) and a strict Content-Security-Policy. All text shown in the screens is escaped to prevent script injection.
- **What would you improve next?** Email notifications, attachments, SLA timers, token expiry, rate limiting, PostgreSQL.
