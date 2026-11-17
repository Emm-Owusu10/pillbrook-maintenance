import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router";
import { describe, expect, it, vi } from "vitest";

import App from "../App.jsx";
import { AuthProvider } from "../auth.jsx";
import { jsonResponse, mockApi } from "../test/mockApi.js";

const TOKEN = "A".repeat(43);
const SIGNED_OUT = jsonResponse(401, { detail: "Not signed in." });
const INVALID = jsonResponse(400, { detail: "This link is not valid or has expired." });
const VERIFY = "POST /api/auth/verify-email";

function Where() {
  const location = useLocation();
  return <p data-testid="where">{location.pathname + location.search + location.hash}</p>;
}

function renderAt(entry) {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <AuthProvider>
        <App />
      </AuthProvider>
      <Where />
    </MemoryRouter>,
  );
}

const verifyCalls = (calls) => calls.filter((c) => c.key === VERIFY);
const where = () => screen.getByTestId("where").textContent;

describe("Confirm your email page", () => {
  it("confirms the address with the code from the link, once, and removes it from the address", async () => {
    const { calls } = mockApi({ "GET /api/auth/me": SIGNED_OUT, [VERIFY]: jsonResponse(200, { verified: true }) });
    renderAt(`/verify-email#token=${TOKEN}`);
    expect(await screen.findByRole("heading", { name: "Your email address is confirmed" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "sign in" })).toBeTruthy();
    expect(verifyCalls(calls)).toHaveLength(1);
    expect(JSON.parse(verifyCalls(calls)[0].options.body)).toEqual({ token: TOKEN });
    expect(where()).toBe("/verify-email");
  });

  it("explains an invalid or expired link and offers a new one", async () => {
    mockApi({ "GET /api/auth/me": SIGNED_OUT, [VERIFY]: INVALID });
    renderAt(`/verify-email#token=${TOKEN}`);
    expect(await screen.findByRole("heading", { name: "This link is not valid" })).toBeTruthy();
    expect((await screen.findByRole("alert")).textContent).toBe("This link is not valid or has expired.");
    expect(screen.getByRole("button", { name: "Send a new link" })).toBeTruthy();
  });

  it("removes the code from the address even when the link turns out to be invalid", async () => {
    mockApi({ "GET /api/auth/me": SIGNED_OUT, [VERIFY]: INVALID });
    renderAt(`/verify-email#token=${TOKEN}`);
    await screen.findByRole("heading", { name: "This link is not valid" });
    expect(where()).toBe("/verify-email");
  });

  it("shows how to get a link when the address has no code", async () => {
    const { calls } = mockApi({ "GET /api/auth/me": SIGNED_OUT });
    renderAt("/verify-email");
    expect(await screen.findByRole("heading", { name: "Confirm your email address" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Send a new link" })).toBeTruthy();
    expect(verifyCalls(calls)).toHaveLength(0);
  });

  it("does not send a code that cannot be real", async () => {
    const { calls } = mockApi({ "GET /api/auth/me": SIGNED_OUT });
    renderAt("/verify-email#token=abc");
    expect(await screen.findByRole("heading", { name: "Confirm your email address" })).toBeTruthy();
    expect(verifyCalls(calls)).toHaveLength(0);
  });

  it("offers a retry when the server cannot be reached, without losing the code", async () => {
    let attempts = 0;
    const { calls } = mockApi({
      "GET /api/auth/me": SIGNED_OUT,
      [VERIFY]: () => {
        attempts += 1;
        return attempts === 1 ? new TypeError("Failed to fetch") : jsonResponse(200, { verified: true });
      },
    });
    renderAt(`/verify-email#token=${TOKEN}`);
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("The server cannot be reached. Please try again later.");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: "Your email address is confirmed" })).toBeTruthy();
    expect(verifyCalls(calls).map((c) => JSON.parse(c.options.body).token)).toEqual([TOKEN, TOKEN]);
  });

  it("reports an unexpected server answer plainly", async () => {
    mockApi({ "GET /api/auth/me": SIGNED_OUT, [VERIFY]: jsonResponse(500, { detail: "Internal server error" }) });
    renderAt(`/verify-email#token=${TOKEN}`);
    expect((await screen.findByRole("alert")).textContent).toBe("Something went wrong. Please try again.");
  });

  it("never writes the code to browser storage", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    mockApi({ "GET /api/auth/me": SIGNED_OUT, [VERIFY]: jsonResponse(200, { verified: true }) });
    renderAt(`/verify-email#token=${TOKEN}`);
    await screen.findByRole("heading", { name: "Your email address is confirmed" });
    expect(setItem).not.toHaveBeenCalled();
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });

  it("lets a person with an expired link ask for a new one", async () => {
    const { calls } = mockApi({
      "GET /api/auth/me": SIGNED_OUT,
      [VERIFY]: INVALID,
      "POST /api/auth/resend-verification": jsonResponse(202, {
        message: "If that address still needs confirming, a new email is on its way.",
      }),
    });
    renderAt(`/verify-email#token=${TOKEN}`);
    await screen.findByRole("heading", { name: "This link is not valid" });
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "ama@farm-mail.org" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Send a new link" }));
    });
    expect((await screen.findByRole("status")).textContent).toContain("a new email is on its way");
    const resend = calls.find((c) => c.key === "POST /api/auth/resend-verification");
    expect(JSON.parse(resend.options.body)).toEqual({ email: "ama@farm-mail.org" });
  });
});