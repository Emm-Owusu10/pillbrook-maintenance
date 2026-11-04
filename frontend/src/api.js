// The only place the frontend talks to the API.

export class ApiError extends Error {
  constructor(status, problems) {
    // The message never includes what the user submitted.
    super(`Request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.problems = problems; // [{ field, message }]
  }
}

// Kept in memory only, never in browser storage, so a script cannot find it lying around.
let csrfToken = null;
let sessionEndedHandler = null;

export function setCsrfToken(token) {
  csrfToken = token;
}

// Called when a request is refused because the session has ended.
export function setSessionEndedHandler(handler) {
  sessionEndedHandler = handler;
}

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
// A refusal from these addresses is normal (not signed in, wrong password), not an ended session.
const SIGN_IN_PATHS = new Set(["/api/auth/login", "/api/auth/me", "/api/auth/logout"]);

function toProblems(detail) {
  if (Array.isArray(detail)) {
    return detail
      .filter((item) => item && typeof item.message === "string")
      .map((item) => ({ field: String(item.field ?? ""), message: item.message }));
  }
  return typeof detail === "string" ? [{ field: "", message: detail }] : [];
}

export async function apiFetch(path, { method = "GET", body, signal } = {}) {
  // Only our own API: a relative path under /api/. Anything else is refused before any request is made.
  if (typeof path !== "string" || !path.startsWith("/api/")) {
    throw new Error("apiFetch only accepts paths that start with /api/");
  }

  const headers = { Accept: "application/json" };
  const options = { method, headers, credentials: "same-origin", signal };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  // Every request that changes data carries the secret handshake word from sign-in.
  if (csrfToken && !SAFE_METHODS.has(method.toUpperCase())) {
    headers["X-CSRF-Token"] = csrfToken;
  }

  const response = await fetch(path, options);

  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null; // an empty or non-JSON body
  }

  if (!response.ok) {
    if (response.status === 401 && !SIGN_IN_PATHS.has(path) && sessionEndedHandler) {
      sessionEndedHandler();
    }
    throw new ApiError(response.status, toProblems(data?.detail));
  }
  return data;
}