# HelpDesk Pro – Support Ticket Management System

Django + Django REST Framework + SQLite + Django templates (light JS `fetch`) + Postman.

Customers raise tickets, agents resolve them, admins manage users and see stats.
All data goes through a REST API (`/api/v1/`) that is tested in Postman and used by the web screens.

> New to Django? Read **[EXPLAINED.md](EXPLAINED.md)** first – it explains how everything fits together.

---

## 1. Run it (5 minutes)

Needs **Python 3.10+**.

```bash
# 1. create and activate a virtual environment
python -m venv venv
venv\Scripts\activate            # Windows
source venv/bin/activate         # macOS / Linux

# 2. install dependencies
pip install -r requirements.txt

# 3. create the database tables
python manage.py migrate

# 4. load demo data (categories, 4 users, 5 tickets)
python manage.py seed

# 5. start the server
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) and sign in. **Password for every demo user: `Pass@12345`**

| Username  | Role     | Lands on                                       |
| --------- | -------- | ---------------------------------------------- |
| `ravi`  | CUSTOMER | S3 Customer dashboard                          |
| `meera` | CUSTOMER | S3 (a second customer, to test isolation)      |
| `asha`  | AGENT    | S7 Agent queue                                 |
| `admin` | ADMIN    | S9 Admin dashboard (also works at `/admin/`) |

Useful URLs: `/api/v1/` (browsable API) · `/admin/` (Django admin) · `/api/ping/` (Phase 1 check)

## 2. Run the tests

```bash
python manage.py test
```

50 tests covering auth, scoping, the permission matrix, status rules, comments, filters, pagination and the screens.

## 3. Postman

1. Postman → **Import** → select both files in `postman/`:
   `HelpDesk_Pro.postman_collection.json` and `HelpDesk_Pro_Local.postman_environment.json`
2. Pick the environment **HelpDesk Pro – Local** (top right).
3. Make sure the server is running and you ran `python manage.py seed`.
4. Right-click the collection → **Run collection** → Run. Everything should be green (74 requests, 119 tests).

How it works: the *Auth* folder logs in as each role and saves `token_customer`, `token_customer2`, `token_agent`,
`token_admin` into the environment (via the **Tests** tab script). Every other request picks the token for the
role it is testing. Each endpoint is tested for success, **no token → 401** and **wrong role → 403/404**.
The collection can be re-run any number of times; the last folder (*Cleanup*) deletes the ticket it created.

## 4. API summary (base `/api/v1/`)

| Method               | Endpoint                                    | Who                                                   |
| -------------------- | ------------------------------------------- | ----------------------------------------------------- |
| POST                 | `/auth/register/`                         | Anyone (creates a CUSTOMER)                           |
| POST                 | `/auth/login/`                            | Anyone → `{token, user}`                           |
| POST                 | `/auth/logout/`                           | Logged in (revokes the token)                         |
| POST                 | `/auth/change-password/`                  | Logged in (returns a fresh token)                     |
| GET / PATCH          | `/auth/me/`                               | Logged in                                             |
| GET                  | `/users/?role=` · PATCH `/users/{id}/` | Admin                                                 |
| GET                  | `/categories/`                            | Logged in                                             |
| GET / POST           | `/tickets/`                               | Logged in (scoped) / Customer + Admin                 |
| GET / PATCH / DELETE | `/tickets/{id}/`                          | Owner or staff / Owner (status only) or staff / Admin |
| POST                 | `/tickets/{id}/assign/`                   | Agent, Admin                                          |
| GET                  | `/tickets/queue/`                         | Agent, Admin                                          |
| GET                  | `/tickets/summary/`                       | Logged in (counts by status – feeds S3)              |
| GET / POST           | `/tickets/{id}/comments/`                 | Owner or staff                                        |
| GET                  | `/stats/`                                 | Admin                                                 |

Query params on `/tickets/`: `?status=OPEN&priority=HIGH&category=2&assigned_to=me&search=login&ordering=-created_at&page=2&page_size=5`

Authentication header: `Authorization: Bearer <token>`.
Errors always look like `{"detail": "..."}`; form-field validation errors look like `{"field": ["message"]}`.

## 5. Screens

|                       | URL                     | Role                 |
| --------------------- | ----------------------- | -------------------- |
| S1 Login              | `/login/`             | all                  |
| S2 Register           | `/register/`          | all                  |
| S3 Customer dashboard | `/customer/`          | customer, admin      |
| S4 Ticket list        | `/tickets/`           | all (scoped by role) |
| S5 Create ticket      | `/tickets/new/`       | customer, admin      |
| S6 Ticket detail      | `/tickets/<id>/`      | all                  |
| S7 Agent queue        | `/agent/queue/`       | agent, admin         |
| S8 Profile            | `/profile/`           | all                  |
| S9 Admin dashboard    | `/admin-panel/`       | admin                |
| S10 Admin users       | `/admin-panel/users/` | admin                |

## 6. Screenshot checklist (from the task)

1. **DRF browsable API root** – open `/api/v1/` in the browser (click *Log in* top-right first; use `admin`).
2. **Postman login + token saved** – run *Auth → Login – customer (ravi)*, show the **Tests** tab script and the environment's `token_customer`.
3. **Postman 403 / 404 for a customer opening another customer's ticket** – see *Tickets → Get ticket – another customer gets 404*.
   For a literal **403** screenshot use *Users → List users – customer forbidden* or *Cleanup → Delete ticket – customer forbidden*.
   (See "Design decisions" below for why a stranger's ticket is a 404.)
4. **Django admin showing users with roles** – `/admin/` → Users.
5. **Screens S1–S10** in the browser (log in as each role).
6. **Terminal with all tests passing** – `python manage.py test`.

## 7. Design decisions (where the task document was ambiguous)

- **Other people's tickets return 404, not 403.** The permission matrix says "No (404)". Queryset scoping means the ticket simply doesn't exist for that user, which also avoids revealing that it exists. The checklist item mentions 403; if your manager insists, change `get_queryset` to not filter and let `IsOwnerOrStaff` return 403 – the unit test `test_customer_gets_404_for_others_ticket` would then need updating.
- **Agents cannot create tickets** (permission matrix: "No"). Customers and admins can.
- **Agents see** tickets assigned to them + the unassigned queue (queryset-scoping rule); not other agents' tickets.
- **Status rules**: staff move one step at a time `OPEN → IN_PROGRESS → RESOLVED → CLOSED`, and may reopen a RESOLVED/CLOSED ticket. Customers may only do `RESOLVED → CLOSED` or reopen to `OPEN`, and may not edit any other field.
- **Assigning** a ticket does not change its status; the agent moves it to IN_PROGRESS themselves. Only unassigned, non-closed tickets can be assigned.
- **Token header uses `Bearer`** (DRF's default is `Token`) so Postman's built-in *Bearer Token* auth type works unchanged.
- `/api/tickets-basic/` (Phase 1 teaching view) has no login, so it only answers when `DEBUG = True`.
- The task's Phase 7 row is cut off in the document; it is treated as "web screens with fetch" (that is what S1–S10 are).

## 8. Troubleshooting

- **`no such table`** → run `python manage.py migrate`.
- **Changed `AUTH_USER_MODEL` / models and migrations are a mess** → delete `db.sqlite3` and every `migrations/0*.py`, then `makemigrations accounts tickets`, `migrate`, `seed`.
- **Postman `500` on a POST** → the URL must end with `/` (e.g. `/auth/login/`).
- **Postman scripts: don't name a variable `data`** – it is reserved by Postman's sandbox. The collection uses `resp`.
- **401 on every call** → the token variable is empty. Run the *Auth* folder first and check the correct environment is selected.
- **Port busy** → `python manage.py runserver 8080`.

## 9. Project layout

```
config/      settings, root urls, error-format handler
accounts/    custom User (+role), register/login/logout/me/change-password, /users/
tickets/     Category, Ticket, Comment · serializers · permissions · viewsets · seed command · tests
web/         HTML templates + CSS + JS for screens S1–S10
postman/     collection + environment
CHANGELOG.md   what changed in each phase and every bug found while testing
```
