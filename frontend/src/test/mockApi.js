import { vi } from "vitest";

export const TOKEN = "t".repeat(64);
export const ME = {
  user: {
    user_id: "11111111-1111-1111-1111-111111111111",
    name: "Ama Mensah",
    email: "ama@farm-mail.org",
    role: "user",
  },
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