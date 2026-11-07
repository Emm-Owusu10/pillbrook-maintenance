import { vi } from "vitest";

export const TOKEN = "t".repeat(64);

export const USER_PERMISSIONS = [
  "confirm_own_request",
  "edit_own_request",
  "submit_request",
  "view_own_notifications",
  "view_own_requests",
];

export const ME = {
  user: {
    user_id: "11111111-1111-1111-1111-111111111111",
    name: "Ama Mensah",
    email: "ama@farm-mail.org",
    role: "user",
  },
  permissions: USER_PERMISSIONS,
  csrf_token: TOKEN,
};

export const ADMIN_ME = {
  user: {
    user_id: "22222222-2222-2222-2222-222222222222",
    name: "Kofi Boateng",
    email: "kofi@farm-mail.org",
    role: "admin",
  },
  permissions: [
    ...USER_PERMISSIONS,
    "change_access_code",
    "close_requests",
    "manage_users",
    "view_access_code",
    "view_all_requests",
    "view_audit_log",
    "view_reports",
  ],
  csrf_token: TOKEN,
};

export function jsonResponse(status, body = null) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

// routes: { "GET /api/auth/me": response | Error | (options) => response | Error }
// An Error is thrown, which looks to the app like a lost connection.
export function mockApi(routes) {
  const calls = [];
  const fetchMock = vi.fn(async (path, options = {}) => {
    const key = `${options.method ?? "GET"} ${path}`;
    calls.push({ key, options });
    const route = routes[key];
    if (route === undefined) throw new Error(`Unexpected request: ${key}`);
    const value = typeof route === "function" ? route(options) : route;
    if (value instanceof Error) throw value;
    return value;
  });
  vi.stubGlobal("fetch", fetchMock);
  return { fetchMock, calls };
}