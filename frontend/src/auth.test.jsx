import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { apiFetch } from "./api.js";
import { AuthProvider, useAuth } from "./auth.jsx";
import { jsonResponse, ME, mockApi, TOKEN } from "./test/mockApi.js";

function Probe() {
  const auth = useAuth();
  return (
    <div>
      <p data-testid="status">{auth.status}</p>
      <p data-testid="user">{auth.user ? auth.user.email : "none"}</p>
      <p data-testid="notice">{auth.notice}</p>
      <p data-testid="onpurpose">{String(auth.signedOutOnPurpose)}</p>
      <button onClick={() => auth.signIn("ama@farm-mail.org", "a long enough password").catch(() => {})}>
        sign in
      </button>
      <button onClick={() => auth.signOut().catch(() => {})}>sign out</button>
      <button onClick={auth.retry}>retry</button>
      <button onClick={() => apiFetch("/api/things", { method: "POST", body: {} }).catch(() => {})}>
        change something
      </button>
    </div>
  );
}

const show = (name) => screen.getByTestId(name).textContent;
const waitForStatus = (expected) => waitFor(() => expect(show("status")).toBe(expected));
const renderProbe = () =>
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  );

describe("AuthProvider", () => {
  it("starts loading, then shows signed out when there is no session", async () => {
    mockApi({ "GET /api/auth/me": jsonResponse(401, { detail: "Not signed in." }) });
    renderProbe();
    expect(show("status")).toBe("loading");
    await waitForStatus("signedOut");
    expect(show("user")).toBe("none");
    expect(show("onpurpose")).toBe("false");
  });

  it("shows signed in when the server already holds a session", async () => {
    mockApi({ "GET /api/auth/me": jsonResponse(200, ME) });
    renderProbe();
    await waitForStatus("signedIn");
    expect(show("user")).toBe(ME.user.email);
  });

  it("reports an unreachable server and recovers when asked to retry", async () => {
    let attempts = 0;
    mockApi({
      "GET /api/auth/me": () => {
        attempts += 1;
        return attempts === 1 ? new TypeError("Failed to fetch") : jsonResponse(200, ME);
      },
    });
    renderProbe();
    await waitForStatus("unreachable");
    fireEvent.click(screen.getByText("retry"));
    await waitForStatus("signedIn");
  });

  it("signs in, and later changes carry the CSRF token", async () => {
    const { calls } = mockApi({
      "GET /api/auth/me": jsonResponse(401, { detail: "Not signed in." }),
      "POST /api/auth/login": jsonResponse(200, ME),
      "POST /api/things": jsonResponse(200, {}),
    });
    renderProbe();
    await waitForStatus("signedOut");
    fireEvent.click(screen.getByText("sign in"));
    await waitForStatus("signedIn");
    expect(show("user")).toBe(ME.user.email);

    fireEvent.click(screen.getByText("change something"));
    await waitFor(() => expect(calls.some((c) => c.key === "POST /api/things")).toBe(true));
    const change = calls.find((c) => c.key === "POST /api/things");
    expect(change.options.headers["X-CSRF-Token"]).toBe(TOKEN);
  });

  it("signs out, using the token, and then forgets it", async () => {
    const { calls } = mockApi({
      "GET /api/auth/me": jsonResponse(200, ME),
      "POST /api/auth/logout": jsonResponse(204),
      "POST /api/things": jsonResponse(200, {}),
    });
    renderProbe();
    await waitForStatus("signedIn");
    fireEvent.click(screen.getByText("sign out"));
    await waitForStatus("signedOut");
    expect(show("onpurpose")).toBe("true");
    const logout = calls.find((c) => c.key === "POST /api/auth/logout");
    expect(logout.options.headers["X-CSRF-Token"]).toBe(TOKEN);

    fireEvent.click(screen.getByText("change something"));
    await waitFor(() => expect(calls.some((c) => c.key === "POST /api/things")).toBe(true));
    const change = calls.find((c) => c.key === "POST /api/things");
    expect(change.options.headers["X-CSRF-Token"]).toBeUndefined();
  });

  it("stays signed in when signing out fails", async () => {
    const { calls } = mockApi({
      "GET /api/auth/me": jsonResponse(200, ME),
      "POST /api/auth/logout": new TypeError("Failed to fetch"),
    });
    renderProbe();
    await waitForStatus("signedIn");
    fireEvent.click(screen.getByText("sign out"));
    await waitFor(() => expect(calls.some((c) => c.key === "POST /api/auth/logout")).toBe(true));
    expect(show("status")).toBe("signedIn");
  });

  it("signs out here when the server says the session was already gone", async () => {
    mockApi({
      "GET /api/auth/me": jsonResponse(200, ME),
      "POST /api/auth/logout": jsonResponse(401, { detail: "Not signed in." }),
    });
    renderProbe();
    await waitForStatus("signedIn");
    fireEvent.click(screen.getByText("sign out"));
    await waitForStatus("signedOut");
    expect(show("notice")).toBe("");
  });

  it("returns to signed out with a notice when a later request shows the session has ended", async () => {
    mockApi({
      "GET /api/auth/me": jsonResponse(200, ME),
      "POST /api/things": jsonResponse(401, { detail: "Not signed in." }),
    });
    renderProbe();
    await waitForStatus("signedIn");
    fireEvent.click(screen.getByText("change something"));
    await waitForStatus("signedOut");
    expect(show("notice")).toBe("Your session has ended. Please sign in again.");
    expect(show("onpurpose")).toBe("false");
  });

  it("never writes anything to browser storage", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    mockApi({
      "GET /api/auth/me": jsonResponse(401, { detail: "Not signed in." }),
      "POST /api/auth/login": jsonResponse(200, ME),
    });
    renderProbe();
    await waitForStatus("signedOut");
    fireEvent.click(screen.getByText("sign in"));
    await waitForStatus("signedIn");
    expect(setItem).not.toHaveBeenCalled();
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });
});