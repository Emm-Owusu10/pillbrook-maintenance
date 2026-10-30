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
  // Step 2.2 adds the CSRF header here for POST, PATCH and DELETE requests.

  const response = await fetch(path, options);

  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null; // an empty or non-JSON body
  }

  if (!response.ok) {
    throw new ApiError(response.status, toProblems(data?.detail));
  }
  return data;
}