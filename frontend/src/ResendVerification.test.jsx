import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ResendVerification from "./ResendVerification.jsx";
import { jsonResponse, mockApi } from "./test/mockApi.js";

const MESSAGE = "If that address still needs confirming, a new email is on its way.";
const KEY = "POST /api/auth/resend-verification";

describe("ResendVerification", () => {
  it("sends the address and shows the server's message", async () => {
    const { calls } = mockApi({ [KEY]: jsonResponse(202, { message: MESSAGE }) });
    render(<ResendVerification initialEmail="ama@farm-mail.org" />);
    fireEvent.click(screen.getByRole("button", { name: "Send a new link" }));
    const status = await screen.findByRole("status");
    expect(status.textContent).toBe(MESSAGE);
    expect(JSON.parse(calls[0].options.body)).toEqual({ email: "ama@farm-mail.org" });
  });

  it("asks for an address instead of sending an empty form", async () => {
    const { calls } = mockApi({ [KEY]: jsonResponse(202, { message: MESSAGE }) });
    render(<ResendVerification />);
    fireEvent.click(screen.getByRole("button", { name: "Send a new link" }));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Enter your email address.");
    expect(calls).toHaveLength(0);
  });

  it("says so when the request cannot be sent", async () => {
    mockApi({ [KEY]: new TypeError("Failed to fetch") });
    render(<ResendVerification initialEmail="ama@farm-mail.org" />);
    fireEvent.click(screen.getByRole("button", { name: "Send a new link" }));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("The request could not be sent. Please try again later.");
  });

  it("disables the button while sending", async () => {
    let release;
    const pending = new Promise((resolve) => {
      release = () => resolve(jsonResponse(202, { message: MESSAGE }));
    });
    const { calls } = mockApi({ [KEY]: () => pending });
    render(<ResendVerification initialEmail="ama@farm-mail.org" />);
    fireEvent.click(screen.getByRole("button", { name: "Send a new link" }));
    const busy = await screen.findByRole("button", { name: "Sending..." });
    expect(busy.disabled).toBe(true);
    fireEvent.click(busy);
    expect(calls).toHaveLength(1);
    await act(async () => {
      release();
    });
    expect(await screen.findByRole("status")).toBeTruthy();
  });
});