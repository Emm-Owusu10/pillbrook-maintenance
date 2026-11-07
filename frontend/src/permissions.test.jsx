import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AuthProvider, useAuth } from "./auth.jsx";
import { ADMIN_ME, jsonResponse, ME, mockApi } from "./test/mockApi.js";

function Probe() {
  const auth = useAuth();
  return (
    <div>
      <p data-testid="status">{auth.status}</p>
      <p data-testid="list">{auth.permissions.join(",")}</p>
      <p data-testid="can-audit">{String(auth.can("view_audit_log"))}</p>
      <p data-testid="can-submit">{String(auth.can("submit_request"))}</p>
      <button onClick={() => auth.signOut().catch(() => {})}>sign out</button>
      <button onClick={() => auth.signIn("kofi@farm-mail.org", "a long enough password").catch(() => {})}>
        sign in
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

describe("permissions in the sign-in state", () => {
  it("knows what an Administrator may do", async () => {
    mockApi({ "GET /api/auth/me": jsonResponse(200, ADMIN_ME) });
    renderProbe();
    await waitForStatus("signedIn");
    expect(show("can-audit")).toBe("true");
    expect(show("can-submit")).toBe("true");
  });

  it("knows that a Farm User may not use Administrator functions", async () => {
    mockApi({ "GET /api/auth/me": jsonResponse(200, ME) });
    renderProbe();
    await waitForStatus("signedIn");
    expect(show("can-audit")).toBe("false");
    expect(show("can-submit")).toBe("true");
  });

  it("takes the permissions from the sign-in reply", async () => {
    mockApi({
      "GET /api/auth/me": jsonResponse(401, { detail: "Not signed in." }),
      "POST /api/auth/login": jsonResponse(200, ADMIN_ME),
    });
    renderProbe();
    await waitForStatus("signedOut");
    expect(show("can-audit")).toBe("false");
    fireEvent.click(screen.getByText("sign in"));
    await waitForStatus("signedIn");
    expect(show("can-audit")).toBe("true");
  });

  it("forgets them at sign-out", async () => {
    mockApi({
      "GET /api/auth/me": jsonResponse(200, ADMIN_ME),
      "POST /api/auth/logout": jsonResponse(204),
    });
    renderProbe();
    await waitForStatus("signedIn");
    fireEvent.click(screen.getByText("sign out"));
    await waitForStatus("signedOut");
    expect(show("list")).toBe("");
    expect(show("can-audit")).toBe("false");
  });

  it("treats a reply without permissions as having none", async () => {
    const { permissions, ...withoutPermissions } = ME; // eslint-disable-line no-unused-vars
    mockApi({ "GET /api/auth/me": jsonResponse(200, withoutPermissions) });
    renderProbe();
    await waitForStatus("signedIn");
    expect(show("list")).toBe("");
    expect(show("can-submit")).toBe("false");
  });
});