# Changelog

Everything listed under "Found by" was a real issue that a test, Postman run or review exposed, and how it was fixed.
Re-run `python manage.py test` and the Postman collection after every fix.

## Phase 8 – Polish
- Added `seed` command, README, EXPLAINED.md, 50 unit tests.
- **Found by:** unit test run – `/api/tickets-basic/` returned 404 under `manage.py test`.
  **Cause:** Django forces `DEBUG=False` in tests and the view is debug-only. **Fix:** test now uses `override_settings(DEBUG=True)`; a second test proves it is disabled when `DEBUG=False`.
- **Found by:** unit test run – tests took ~56 s. **Fix:** MD5 password hasher while running tests only.

## Phase 7 – Web screens
- Screens S1–S10 (templates + `fetch`), role-based redirect after login, token in `localStorage`.
- **Found by:** browser walkthrough – the 404 message for a customer opening someone else's ticket was
  `"No Ticket matches the given query."`, leaking an internal model name.
  **Fix:** the exception handler now returns `{"detail": "Not found."}` for every 404 (so a stranger's ticket and a
  non-existent ticket look identical). Test: `test_404_does_not_leak_details`.
- All user-supplied text is escaped before it is put into the page (verified with a ticket titled `<b>test</b>`).

## Phase 6 – Postman + project update
- Collection `HelpDesk Pro` (folders Auth, Tickets, Comments, Users, Stats, Cleanup): 74 requests, 119 assertions. Each endpoint tested for success, no token (401) and wrong role (403/404).
- **Found by:** first collection run – every login test failed with `SyntaxError: Identifier 'data' has already been declared`, so no token was saved and the rest of the run returned 401.
  **Cause:** `data` is a reserved global in Postman's script sandbox (iteration data). **Fix:** renamed to `resp`.
- **Found by:** first collection run – `POST` requests returned 500.
  **Cause:** the request URL had lost its trailing slash and Django cannot redirect a POST (`APPEND_SLASH`). **Fix:** URLs in the collection end with `/`.

## Phase 5 – Extras
- Filtering (`status`, `priority`, `category`, `assigned_to=me`), `search`, `ordering`, pagination (`page`, `page_size`).
- `POST /tickets/{id}/assign/`, `GET /tickets/queue/`, `GET /tickets/summary/`, `GET /stats/`.
- Admin cannot deactivate or change the role of their own account (would lock them out).

## Phase 4 – Permissions
- `IsAgent`, `IsAdmin`, `IsAgentOrAdmin`, `IsCustomerOrAdmin`, object-level `IsOwnerOrStaff`.
- Queryset scoping per role (customer: own; agent: assigned + unassigned; admin: all).
- Internal comments hidden from customers in the list, the nested ticket detail **and** `comment_count`.

## Phase 3 – Authentication
- Custom `User` (`role`, `phone`); superusers are forced to role ADMIN.
- Register (always CUSTOMER – a `role` in the request body is ignored), login, logout (token revoked), change password (token rotated), `/auth/me/` (role is read-only).
- Token auth with the `Bearer` keyword + session auth for the browsable API.

## Phase 2 – DRF
- `ModelSerializer`s, nested comments (`SerializerMethodField`), status rules in `validate()`, `ModelViewSet` + router.

## Phase 1 – Basic API with plain Django
- `/api/ping/` and `/api/tickets-basic/` using `JsonResponse`.
- Security review: `/api/tickets-basic/` has no authentication, so it only answers when `DEBUG=True`.
