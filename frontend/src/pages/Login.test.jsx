import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import App from "../App.jsx";
import { AuthProvider } from "../auth.jsx";
import { jsonResponse, ME, mockApi } from "../test/mockApi.js";

const SIGNED_OUT = jsonResponse(401, { detail: "Not signed in." });

function renderApp(entry = "/login") {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );
}

function fill(email, password) {
  fireEvent.change(screen.getByLabelText("Email address"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
}

const submit = () => fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
const loginCalls = (calls) => calls.filter((c) => c.key === "POST /api/auth/login");

describe("Sign-in page", () => {
  it("shows the form, with the password hidden until asked", async () => {
    mockApi({ "GET /api/auth/me": SIGNED_OUT });
    renderApp();
    const email = await screen.findByLabelText("Email address");
    const password = screen.getByLabelText("Password");
    expect(email.getAttribute("autocomplete")).toBe("username");
    expect(password.getAttribute("autocomplete")).toBe("current-password");
    expect(password.type).toBe("password");

    fireEvent.click(screen.getByLabelText("Show password"));
    expect(password.type).toBe("text");
    fireEvent.click(screen.getByLabelText("Show password"));
    expect(password.type).toBe("password");
  });

  it("signs in and goes to the home page", async () => {
    const { calls } = mockApi({
      "GET /api/auth/me": SIGNED_OUT,
      "POST /api/auth/login": jsonResponse(200, ME),
    });
    renderApp();
    await screen.findByLabelText("Email address");
    fill("ama@farm-mail.org", "a long enough password");
    submit();
    expect(await screen.findByRole("heading", { name: "Welcome, Ama Mensah" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sign out" })).toBeTruthy();
    expect(loginCalls(calls)).toHaveLength(1);
  });

  it("trims the email but never touches the password", async () => {
    const { calls } = mockApi({
      "GET /api/auth/me": SIGNED_OUT,
      "POST /api/auth/login": jsonResponse(200, ME),
    });
    renderApp();
    await screen.findByLabelText("Email address");
    fill("  ama@farm-mail.org  ", " a password  with spaces ");
    submit();
    await screen.findByRole("heading", { name: "Welcome, Ama Mensah" });
    expect(JSON.parse(loginCalls(calls)[0].options.body)).toEqual({
      email: "ama@farm-mail.org",
      password: " a password  with spaces ",
    });
  });

  it("shows the server's message after a wrong password, keeps the email and clears the password", async () => {
    mockApi({
      "GET /api/auth/me": SIGNED_OUT,
      "POST /api/auth/login": jsonResponse(401, { detail: "Incorrect email or password." }),
    });
    renderApp();
    await screen.findByLabelText("Email address");
    fill("ama@farm-mail.org", "the wrong password");
    submit();
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Incorrect email or password.");
    expect(screen.getByLabelText("Email address").value).toBe("ama@farm-mail.org");
    expect(screen.getByLabelText("Password").value).toBe("");
    expect(screen.getByRole("button", { name: "Sign in" }).disabled).toBe(false);
  });

  it("shows the lock message", async () => {
    mockApi({
      "GET /api/auth/me": SIGNED_OUT,
      "POST /api/auth/login": jsonResponse(429, {
        detail: "Too many failed attempts. Try again in 10 minutes.",
      }),
    });
    renderApp();
    await screen.findByLabelText("Email address");
    fill("ama@farm-mail.org", "whatever password");
    submit();
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Too many failed attempts. Try again in 10 minutes.");
  });

  it("says when the server cannot be reached", async () => {
    mockApi({
      "GET /api/auth/me": SIGNED_OUT,
      "POST /api/auth/login": new TypeError("Failed to fetch"),
    });
    renderApp();
    await screen.findByLabelText("Email address");
    fill("ama@farm-mail.org", "whatever password");
    submit();
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("The server cannot be reached. Please try again later.");
  });

  it("does not send an empty form", async () => {
    const { calls } = mockApi({ "GET /api/auth/me": SIGNED_OUT });
    renderApp();
    await screen.findByLabelText("Email address");
    submit();
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Enter your email address and your password.");
    expect(loginCalls(calls)).toHaveLength(0);
  });

  it("disables the button while signing in", async () => {
    let release;
    const pending = new Promise((resolve) => {
      release = () => resolve(jsonResponse(200, ME));
    });
    const { calls } = mockApi({
      "GET /api/auth/me": SIGNED_OUT,
      "POST /api/auth/login": () => pending,
    });
    renderApp();
    await screen.findByLabelText("Email address");
    fill("ama@farm-mail.org", "a long enough password");
    submit();

    const busy = await screen.findByRole("button", { name: "Signing in..." });
    expect(busy.disabled).toBe(true);
    fireEvent.click(busy);
    expect(loginCalls(calls)).toHaveLength(1);

    await act(async () => {
      release();
    });
    expect(await screen.findByRole("heading", { name: "Welcome, Ama Mensah" })).toBeTruthy();
  });

  it("returns a signed-out visitor to the page they asked for", async () => {
    mockApi({
      "GET /api/auth/me": SIGNED_OUT,
      "POST /api/auth/login": jsonResponse(200, ME),
    });
    renderApp("/account");
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeTruthy();
    fill("ama@farm-mail.org", "a long enough password");
    submit();
    expect(await screen.findByRole("heading", { name: "My account" })).toBeTruthy();
  });

  it("ignores a destination outside this site", async () => {
    mockApi({
      "GET /api/auth/me": SIGNED_OUT,
      "POST /api/auth/login": jsonResponse(200, ME),
    });
    renderApp({ pathname: "/login", state: { from: "//evil.example/steal" } });
    await screen.findByLabelText("Email address");
    fill("ama@farm-mail.org", "a long enough password");
    submit();
    expect(await screen.findByRole("heading", { name: "Welcome, Ama Mensah" })).toBeTruthy();
  });

  it("sends a signed-in visitor away from the sign-in page", async () => {
    mockApi({ "GET /api/auth/me": jsonResponse(200, ME) });
    renderApp("/login");
    expect(await screen.findByRole("heading", { name: "Welcome, Ama Mensah" })).toBeTruthy();
  });
});