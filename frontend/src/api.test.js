import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiFetch, setCsrfToken, setSessionEndedHandler } from "./api.js";

afterEach(() => {
  setCsrfToken(null);
  setSessionEndedHandler(null);
});

function answer(status, body) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("apiFetch", () => {
  it("returns the parsed JSON on success", async () => {
    answer(200, { status: "ok" });
    expect(await apiFetch("/api/health")).toEqual({ status: "ok" });
  });

  it("sends same-origin credentials and asks for JSON", async () => {
    const fetchMock = answer(200, {});
    await apiFetch("/api/health");
    const [path, options] = fetchMock.mock.calls[0];
    expect(path).toBe("/api/health");
    expect(options.credentials).toBe("same-origin");
    expect(options.method).toBe("GET");
    expect(options.headers.Accept).toBe("application/json");
  });

  it("refuses addresses outside /api/ without making a request", async () => {
    const fetchMock = answer(200, {});
    for (const path of ["https://evil.example/x", "//evil.example/api/x", "/health", "api/health", 5]) {
      await expect(apiFetch(path)).rejects.toThrow("/api/");
    }
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sends a JSON body with its content type", async () => {
    const fetchMock = answer(201, {});
    await apiFetch("/api/things", { method: "POST", body: { a: 1 } });
    const [, options] = fetchMock.mock.calls[0];
    expect(options.body).toBe('{"a":1}');
    expect(options.headers["Content-Type"]).toBe("application/json");
  });

  it("throws an ApiError with the status and the validation problems", async () => {
    answer(422, { detail: [{ field: "password", message: "too short" }, { unrelated: true }] });
    const error = await apiFetch("/api/x").catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(422);
    expect(error.problems).toEqual([{ field: "password", message: "too short" }]);
  });

  it("turns a plain text detail into one problem", async () => {
    answer(500, { detail: "Internal server error" });
    const error = await apiFetch("/api/x").catch((e) => e);
    expect(error.problems).toEqual([{ field: "", message: "Internal server error" }]);
  });

  it("copes with an error response that is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        json: async () => {
          throw new Error("not json");
        },
      }),
    );
    const error = await apiFetch("/api/x").catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(502);
    expect(error.problems).toEqual([]);
  });

  it("passes network failures on to the caller", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(apiFetch("/api/x")).rejects.toThrow(TypeError);
  });

  it("never puts the submitted body in the error", async () => {
    answer(422, { detail: [{ field: "password", message: "too short" }] });
    const error = await apiFetch("/api/x", { method: "POST", body: { password: "hunter-two" } }).catch(
      (e) => e,
    );
    expect(error.message).not.toContain("hunter-two");
    expect(JSON.stringify(error.problems)).not.toContain("hunter-two");
  });
});

describe("apiFetch and the CSRF token", () => {
  it("adds the token to every request that changes data", async () => {
    const fetchMock = answer(200, {});
    setCsrfToken("token-123");
    await apiFetch("/api/things", { method: "POST", body: {} });
    await apiFetch("/api/things/1", { method: "PATCH", body: {} });
    await apiFetch("/api/things/1", { method: "DELETE" });
    for (const [, options] of fetchMock.mock.calls) {
      expect(options.headers["X-CSRF-Token"]).toBe("token-123");
    }
  });

  it("never adds the token to reads", async () => {
    const fetchMock = answer(200, {});
    setCsrfToken("token-123");
    await apiFetch("/api/things");
    expect(fetchMock.mock.calls[0][1].headers["X-CSRF-Token"]).toBeUndefined();
  });

  it("sends no token header when there is no token", async () => {
    const fetchMock = answer(200, {});
    await apiFetch("/api/things", { method: "POST", body: {} });
    expect(fetchMock.mock.calls[0][1].headers["X-CSRF-Token"]).toBeUndefined();
  });
});

describe("apiFetch and ended sessions", () => {
  it("tells the app when a request is refused because the session has ended", async () => {
    answer(401, { detail: "Not signed in." });
    const handler = vi.fn();
    setSessionEndedHandler(handler);
    await expect(apiFetch("/api/things")).rejects.toBeInstanceOf(ApiError);
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("does not treat a refusal at sign-in as an ended session", async () => {
    answer(401, { detail: "Incorrect email or password." });
    const handler = vi.fn();
    setSessionEndedHandler(handler);
    for (const path of ["/api/auth/login", "/api/auth/me", "/api/auth/logout"]) {
      await apiFetch(path).catch(() => {});
    }
    expect(handler).not.toHaveBeenCalled();
  });
});