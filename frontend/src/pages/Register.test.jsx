import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import App from "../App.jsx";
import { AuthProvider } from "../auth.jsx";
import { jsonResponse, ME, mockApi } from "../test/mockApi.js";

const SIGNED_OUT = jsonResponse(401, { detail: "Not signed in." });
const REGISTER = "POST /api/auth/register";
const CREATED = jsonResponse(201, { verification_required: false, verification_email_sent: false });
const PASSWORD = "kiwi lemon river stone";

function renderApp(entry = "/register") {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );
}

function fill({
  name = "Ama Mensah",
  email = "ama@farm-mail.org",
  password = PASSWORD,
  repeat = password,
  code = "K7QM4TRX9WBH",
} = {}) {
  fireEvent.change(screen.getByLabelText("Full name"), { target: { value: name } });
  fireEvent.change(screen.getByLabelText("Email address"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  fireEvent.change(screen.getByLabelText("Repeat the password"), { target: { value: repeat } });
  fireEvent.change(screen.getByLabelText("Farm access code"), { target: { value: code } });
}

const submit = () => fireEvent.click(screen.getByRole("button", { name: "Create account" }));
const registerCalls = (calls) => calls.filter((c) => c.key === REGISTER);

async function openForm(routes) {
  const mocked = mockApi({ "GET /api/auth/me": SIGNED_OUT, ...routes });
  renderApp();
  await screen.findByLabelText("Full name");
  return mocked;
}

describe("Register page", () => {
  it("shows the rules before the password box, hides the passwords until asked, and capitalises the code", async () => {
    await openForm({});
    const password = screen.getByLabelText("Password");
    const repeat = screen.getByLabelText("Repeat the password");
    expect(password.getAttribute("aria-describedby")).toBe("password-rules");
    expect(document.getElementById("password-rules").textContent).toContain("At least 15 characters");
    expect(password.getAttribute("autocomplete")).toBe("new-password");
    expect(password.type).toBe("password");
    expect(repeat.type).toBe("password");

    fireEvent.click(screen.getByLabelText("Show passwords"));
    expect(password.type).toBe("text");
    expect(repeat.type).toBe("text");

    const code = screen.getByLabelText("Farm access code");
    fireEvent.change(code, { target: { value: "k7qm-4trx" } });
    expect(code.value).toBe("K7QM-4TRX");
  });

  it("creates the account and goes to the sign-in page with a notice", async () => {
    const { calls } = await openForm({ [REGISTER]: CREATED });
    fill();
    submit();
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeTruthy();
    expect(screen.getByRole("status").textContent).toBe("Account created. You can now sign in.");
    expect(JSON.parse(registerCalls(calls)[0].options.body)).toEqual({
      name: "Ama Mensah",
      email: "ama@farm-mail.org",
      password: PASSWORD,
      access_code: "K7QM4TRX9WBH",
    });
  });

  it("asks the person to check their email when verification is required", async () => {
    await openForm({ [REGISTER]: jsonResponse(201, { verification_required: true, verification_email_sent: true }) });
    fill();
    submit();
    expect(await screen.findByRole("heading", { name: "Check your email" })).toBeTruthy();
    expect(screen.getByText("ama@farm-mail.org")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Send a new link" })).toBeTruthy();
  });

  it("says so when the confirmation email could not be sent", async () => {
    await openForm({ [REGISTER]: jsonResponse(201, { verification_required: true, verification_email_sent: false }) });
    fill();
    submit();
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("could not be sent");
  });

  it("will not send when the two passwords differ", async () => {
    const { calls } = await openForm({ [REGISTER]: CREATED });
    fill({ repeat: "something else entirely" });
    submit();
    expect((await screen.findByRole("alert")).textContent).toBe("The two passwords do not match.");
    expect(registerCalls(calls)).toHaveLength(0);
  });

  it("will not send an incomplete form", async () => {
    const { calls } = await openForm({ [REGISTER]: CREATED });
    submit();
    expect((await screen.findByRole("alert")).textContent).toBe(
      "Enter your name, email address, password and the farm access code.",
    );
    expect(registerCalls(calls)).toHaveLength(0);
  });

  it("shows a wrong-code message, keeps the passwords and puts the cursor in the code box", async () => {
    await openForm({ [REGISTER]: jsonResponse(403, { detail: "The farm access code is not correct." }) });
    fill();
    submit();
    expect((await screen.findByRole("alert")).textContent).toBe("The farm access code is not correct.");
    expect(screen.getByLabelText("Password").value).toBe(PASSWORD);
    expect(screen.getByLabelText("Repeat the password").value).toBe(PASSWORD);
    expect(document.activeElement).toBe(screen.getByLabelText("Farm access code"));
  });

  it("shows the message when registration is not open yet", async () => {
    await openForm({
      [REGISTER]: jsonResponse(403, { detail: "Registration is not open yet. Ask the Administrator." }),
    });
    fill();
    submit();
    expect((await screen.findByRole("alert")).textContent).toBe("Registration is not open yet. Ask the Administrator.");
  });

  it("shows how long registration is paused", async () => {
    await openForm({
      [REGISTER]: jsonResponse(429, {
        detail: "Registration is paused for a few minutes. Try again in 10 minutes.",
      }),
    });
    fill();
    submit();
    expect((await screen.findByRole("alert")).textContent).toContain("Try again in 10 minutes");
  });

  it("puts each problem next to its field and empties the passwords only when the password was refused", async () => {
    await openForm({
      [REGISTER]: jsonResponse(422, {
        detail: [
          { field: "name", message: "Enter your name (1 to 100 characters)." },
          { field: "email", message: "Enter a valid email address." },
          { field: "password", message: "Use at least 15 characters." },
        ],
      }),
    });
    fill();
    submit();
    expect(await screen.findByText("Use at least 15 characters.")).toBeTruthy();
    expect(screen.getByText("Enter your name (1 to 100 characters).")).toBeTruthy();
    expect(screen.getByText("Enter a valid email address.")).toBeTruthy();
    expect(screen.getByLabelText("Password").value).toBe("");
    expect(screen.getByLabelText("Repeat the password").value).toBe("");
    expect(screen.getByLabelText("Full name").value).toBe("Ama Mensah");
    expect(screen.getByLabelText("Farm access code").value).toBe("K7QM4TRX9WBH");
  });

  it("offers sign-in when the address is already registered", async () => {
    await openForm({
      [REGISTER]: jsonResponse(409, { detail: "An account with this email address already exists." }),
    });
    fill();
    submit();
    expect(await screen.findByText("An account with this email address already exists.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Sign in instead" })).toBeTruthy();
    expect(screen.getByLabelText("Password").value).toBe(PASSWORD);
  });

  it("says when the server cannot be reached", async () => {
    await openForm({ [REGISTER]: new TypeError("Failed to fetch") });
    fill();
    submit();
    expect((await screen.findByRole("alert")).textContent).toBe(
      "The server cannot be reached. Please try again later.",
    );
  });

  it("disables the button while creating the account and sends only one request", async () => {
    let release;
    const pending = new Promise((resolve) => {
      release = () => resolve(CREATED);
    });
    const { calls } = await openForm({ [REGISTER]: () => pending });
    fill();
    submit();
    const busy = await screen.findByRole("button", { name: "Creating account..." });
    expect(busy.disabled).toBe(true);
    fireEvent.click(busy);
    expect(registerCalls(calls)).toHaveLength(1);
    await act(async () => {
      release();
    });
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeTruthy();
  });

  it("sends a signed-in visitor to the home page", async () => {
    mockApi({ "GET /api/auth/me": jsonResponse(200, ME) });
    renderApp("/register");
    expect(await screen.findByRole("heading", { name: "Welcome, Ama Mensah" })).toBeTruthy();
  });

  it("is reachable from the sign-in page", async () => {
    mockApi({ "GET /api/auth/me": SIGNED_OUT });
    renderApp("/login");
    const link = await screen.findByRole("link", { name: /create an account/i });
    fireEvent.click(link);
    expect(await screen.findByRole("heading", { name: "Create an account" })).toBeTruthy();
  });

  it("is reachable from the signed-out home page", async () => {
    mockApi({ "GET /api/auth/me": SIGNED_OUT });
    renderApp("/");
    expect(await screen.findByRole("link", { name: /create an account/i })).toBeTruthy();
  });

  it("never writes anything to browser storage", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    await openForm({ [REGISTER]: CREATED });
    fill();
    submit();
    await screen.findByRole("heading", { name: "Sign in" });
    expect(setItem).not.toHaveBeenCalled();
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });
});