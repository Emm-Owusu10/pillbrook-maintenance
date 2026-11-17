import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import { AuthProvider } from "../auth.jsx";
import { jsonResponse, ME, mockApi } from "../test/mockApi.js";
import Home from "./Home.jsx";

const SIGNED_OUT = jsonResponse(401, { detail: "Not signed in." });

function renderHome() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Home />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("Landing page", () => {
  it("tells a signed-out visitor what the system is for and offers two clear actions", async () => {
    mockApi({ "GET /api/auth/me": SIGNED_OUT });
    renderHome();
    expect(await screen.findByRole("heading", { level: 1, name: "Report and track maintenance faults" })).toBeTruthy();
    expect(screen.getByText("Pill Brook Aquatics Ltd.")).toBeTruthy();
    const create = screen.getByRole("link", { name: "Create an account" });
    const signIn = screen.getByRole("link", { name: "Sign in" });
    expect(create.getAttribute("href")).toBe("/register");
    expect(signIn.getAttribute("href")).toBe("/login");
  });

  it("says that the farm access code is needed to create an account", async () => {
    mockApi({ "GET /api/auth/me": SIGNED_OUT });
    renderHome();
    expect(await screen.findByText(/You need the farm access code/)).toBeTruthy();
  });

  it("explains how it works in three steps", async () => {
    mockApi({ "GET /api/auth/me": SIGNED_OUT });
    renderHome();
    expect(await screen.findByRole("heading", { level: 2, name: "How it works" })).toBeTruthy();
    const steps = screen.getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent);
    expect(steps).toEqual(["Report", "Track", "Confirm"]);
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
  });

  it("hides its decorative artwork from assistive technology", async () => {
    mockApi({ "GET /api/auth/me": SIGNED_OUT });
    renderHome();
    await screen.findByRole("heading", { level: 1 });
    const pictures = [...document.querySelectorAll("main svg")];
    expect(pictures.length).toBeGreaterThanOrEqual(2);
    for (const picture of pictures) {
      expect(picture.getAttribute("aria-hidden")).toBe("true");
      expect(picture.getAttribute("focusable")).toBe("false");
    }
  });

  it("uses the full width of the screen for a signed-out visitor", async () => {
    mockApi({ "GET /api/auth/me": SIGNED_OUT });
    renderHome();
    await screen.findByRole("heading", { level: 1 });
    expect(screen.getByRole("main").classList.contains("page")).toBe(false);
  });

  it("greets a signed-in person inside the normal page container", async () => {
    mockApi({ "GET /api/auth/me": jsonResponse(200, ME) });
    renderHome();
    expect(await screen.findByRole("heading", { name: "Welcome, Ama Mensah" })).toBeTruthy();
    expect(screen.getByRole("main").classList.contains("page")).toBe(true);
    expect(screen.queryByRole("link", { name: "Create an account" })).toBeNull();
  });

  it("keeps the normal page container while it checks who is signed in", () => {
    mockApi({ "GET /api/auth/me": () => new Promise(() => {}) });
    renderHome();
    expect(screen.getByRole("main").classList.contains("page")).toBe(true);
  });
});
