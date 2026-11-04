import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import App from "./App.jsx";
import { AuthProvider } from "./auth.jsx";
import { jsonResponse, ME, mockApi, TOKEN } from "./test/mockApi.js";

const SIGNED_OUT = jsonResponse(401, { detail: "Not signed in." });

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("App", () => {
  it("shows the public home page to a signed-out visitor", async () => {
    mockApi({ "GET /api/auth/me": SIGNED_OUT });
    renderAt("/");
    expect(await screen.findByRole("heading", { name: "Report and track maintenance faults" })).toBeTruthy();
    expect(screen.getAllByRole("link", { name: "Sign in" }).length).toBeGreaterThanOrEqual(1);
  });

  it("shows a message while it finds out who is signed in", () => {
    mockApi({ "GET /api/auth/me": () => new Promise(() => {}) }); // never answers
    renderAt("/");
    expect(screen.getByText("Checking your session...")).toBeTruthy();
  });

  it("keeps the status page open to everyone", async () => {
    mockApi({
      "GET /api/auth/me": SIGNED_OUT,
      "GET /api/health": jsonResponse(200, { status: "ok" }),
    });
    renderAt("/status");
    expect(screen.getByRole("heading", { name: "System status" })).toBeTruthy();
    expect(await screen.findByText("The server is running.")).toBeTruthy();
  });

  it("shows a page-not-found message for unknown addresses", async () => {
    mockApi({ "GET /api/auth/me": SIGNED_OUT });
    renderAt("/no-such-page");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeTruthy();
  });

  it("offers a retry when the server cannot be reached at the start", async () => {
    let attempts = 0;
    mockApi({
      "GET /api/auth/me": () => {
        attempts += 1;
        return attempts === 1 ? new TypeError("Failed to fetch") : SIGNED_OUT;
      },
    });
    renderAt("/");
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("The server cannot be reached. Please check your connection.");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: "Report and track maintenance faults" })).toBeTruthy();
  });

  it("shows a signed-in user their name, role and a sign-out button", async () => {
    mockApi({ "GET /api/auth/me": jsonResponse(200, ME) });
    renderAt("/");
    expect(await screen.findByRole("heading", { name: "Welcome, Ama Mensah" })).toBeTruthy();
    expect(screen.getByText("Ama Mensah (Farm User)")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sign out" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "My account" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Sign in" })).toBeNull();
  });

  it("signs out and returns to the public home page", async () => {
    const { calls } = mockApi({
      "GET /api/auth/me": jsonResponse(200, ME),
      "POST /api/auth/logout": jsonResponse(204),
    });
    renderAt("/account");
    await screen.findByRole("heading", { name: "My account" });
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("heading", { name: "Report and track maintenance faults" })).toBeTruthy();
    expect(screen.getAllByRole("link", { name: "Sign in" }).length).toBeGreaterThanOrEqual(1);
    const logout = calls.find((c) => c.key === "POST /api/auth/logout");
    expect(logout.options.headers["X-CSRF-Token"]).toBe(TOKEN);
  });

  it("says so, and stays signed in, when signing out fails", async () => {
    mockApi({
      "GET /api/auth/me": jsonResponse(200, ME),
      "POST /api/auth/logout": new TypeError("Failed to fetch"),
    });
    renderAt("/");
    await screen.findByRole("heading", { name: "Welcome, Ama Mensah" });
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Could not sign out. Check your connection and try again.");
    expect(screen.getByRole("heading", { name: "Welcome, Ama Mensah" })).toBeTruthy();
  });

  it("shows the account page with name, email and role", async () => {
    mockApi({ "GET /api/auth/me": jsonResponse(200, ME) });
    renderAt("/account");
    expect(await screen.findByRole("heading", { name: "My account" })).toBeTruthy();
    expect(screen.getByText("ama@farm-mail.org")).toBeTruthy();
    expect(screen.getByText("Farm User", { selector: "dd" })).toBeTruthy();
  });
});