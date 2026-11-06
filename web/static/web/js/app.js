/*
 * Shared JavaScript for every screen.
 *
 *   api(path, options)   - calls the REST API with the saved token
 *   Auth                 - token / user stored in localStorage
 *   window.pageInit      - each page defines this; it runs after the login check
 */
const API = "/api/v1";
const HOME = { CUSTOMER: "/customer/", AGENT: "/agent/queue/", ADMIN: "/admin-panel/" };

const Auth = {
  token: () => localStorage.getItem("token"),
  user() {
    try { return JSON.parse(localStorage.getItem("user")); } catch { return null; }
  },
  save(token, user) {
    localStorage.setItem("token", token);
    localStorage.setItem("user", JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
  },
};

/** Call the API. Always resolves to {ok, status, data}; never throws on HTTP errors. */
async function api(path, { method = "GET", body = null } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (Auth.token()) headers.Authorization = "Bearer " + Auth.token();
  let res;
  try {
    res = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : null });
  } catch {
    return { ok: false, status: 0, data: { detail: "Cannot reach the server." } };
  }
  let data = null;
  if (res.status !== 204) {
    try { data = await res.json(); } catch { data = null; }
  }
  // Token rejected (expired / logged out elsewhere): back to login.
  if (res.status === 401 && !path.startsWith("/auth/login")) {
    Auth.clear();
    location.href = "/login/?expired=1";
  }
  return { ok: res.ok, status: res.status, data };
}

/** Escape text before putting it in innerHTML (prevents script injection). */
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

const label = (s) => String(s).replace("_", " ");
const fmt = (iso) => new Date(iso).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
const badge = (v) => `<span class="badge ${esc(v)}">${esc(label(v))}</span>`;

/** Turn an error response body into one readable line. */
function errorText(data) {
  if (!data) return "Something went wrong.";
  if (data.detail) return data.detail;
  return Object.entries(data)
    .map(([k, v]) => `${k}: ${[].concat(v).join(" ")}`)
    .join(" | ");
}

/** Show a message in the #banner element. type: "error" | "ok" */
function banner(type, message) {
  const el = document.getElementById("banner");
  if (el) el.innerHTML = message ? `<div class="banner ${type}">${esc(message)}</div>` : "";
}

/** Put each field error under its input: <span class="field-error" data-for="username"> */
function showFieldErrors(form, data) {
  form.querySelectorAll(".field-error").forEach((el) => (el.textContent = ""));
  let unplaced = [];
  Object.entries(data || {}).forEach(([key, val]) => {
    const el = form.querySelector(`.field-error[data-for="${key}"]`);
    const text = [].concat(val).join(" ");
    if (el) el.textContent = text; else unplaced.push(text);
  });
  return unplaced.join(" ");
}

/** Reusable ticket table used by several screens. */
function ticketTable(tickets, { actionsFor = null } = {}) {
  if (!tickets.length) return `<div class="empty">No tickets to show.</div>`;
  const rows = tickets.map((t) => `
    <tr data-href="/tickets/${t.id}/">
      <td>#${t.id}</td>
      <td><b>${esc(t.title)}</b><div class="muted">${esc(t.category.name)}</div></td>
      <td>${badge(t.priority)}</td>
      <td>${badge(t.status)}</td>
      <td>${esc(t.assigned_to || "Unassigned")}</td>
      <td>${esc(fmt(t.created_at))}</td>
      ${actionsFor ? `<td>${actionsFor(t)}</td>` : ""}
    </tr>`).join("");
  return `<div class="table-wrap"><table>
    <thead><tr><th>ID</th><th>Title</th><th>Priority</th><th>Status</th><th>Assigned</th><th>Created</th>${actionsFor ? "<th></th>" : ""}</tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}

function renderNav(user) {
  const links = {
    CUSTOMER: [["/customer/", "Dashboard"], ["/tickets/", "My Tickets"]],
    AGENT: [["/agent/queue/", "Queue"], ["/tickets/", "Tickets"]],
    ADMIN: [["/admin-panel/", "Dashboard"], ["/tickets/", "Tickets"], ["/admin-panel/users/", "Users"]],
  }[user.role];
  const here = location.pathname;
  const nav = document.getElementById("topbar");
  nav.innerHTML = `
    <a class="brand" href="${HOME[user.role]}">HelpDesk Pro</a>
    <nav>${links.map(([href, text]) =>
      `<a href="${href}" class="${here === href ? "active" : ""}">${text}</a>`).join("")}</nav>
    <details class="user-menu">
      <summary><span class="avatar">${esc(user.username[0])}</span><span>${esc(user.username)} ▾</span></summary>
      <div class="menu">
        <div class="role">${esc(user.role)}</div>
        <a href="/profile/">Profile</a>
        <button id="logout-btn" type="button">Log out</button>
      </div>
    </details>`;
  document.getElementById("logout-btn").addEventListener("click", async () => {
    await api("/auth/logout/", { method: "POST" });
    Auth.clear();
    location.href = "/login/";
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  // Click a table row with data-href to open it.
  document.addEventListener("click", (e) => {
    if (e.target.closest("button, a, select, input")) return;
    const row = e.target.closest("tr[data-href]");
    if (row) location.href = row.dataset.href;
  });

  const roles = document.body.dataset.roles; // only set on logged-in screens
  if (roles) {
    const user = Auth.user();
    if (!Auth.token() || !user) { location.href = "/login/"; return; }
    if (!roles.split(",").includes(user.role)) { location.href = HOME[user.role]; return; }
    renderNav(user);
  }
  if (window.pageInit) await window.pageInit(Auth.user());
});
