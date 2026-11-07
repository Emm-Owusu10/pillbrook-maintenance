import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";

import { AuthProvider } from "./auth.jsx";
import RequireAuth from "./RequireAuth.jsx";
import RequirePermission from "./RequirePermission.jsx";
import { ADMIN_ME, jsonResponse, ME, mockApi } from "./test/mockApi.js";

function renderSecretPage() {
  return render(
    <MemoryRouter initialEntries={["/secret"]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<h1>Sign in page</h1>} />
          <Route element={<RequireAuth />}>
            <Route
              path="/secret"
              element={
                <RequirePermission permission="view_audit_log">
                  <p>The audit log</p>
                </RequirePermission>
              }
            />
          </Route>
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("RequirePermission", () => {
  it("shows the page to someone whose role allows it", async () => {
    mockApi({ "GET /api/auth/me": jsonResponse(200, ADMIN_ME) });
    renderSecretPage();
    expect(await screen.findByText("The audit log")).toBeTruthy();
  });

  it("explains, and shows nothing else, to someone whose role does not", async () => {
    mockApi({ "GET /api/auth/me": jsonResponse(200, ME) });
    renderSecretPage();
    expect(await screen.findByRole("heading", { name: "You don't have permission" })).toBeTruthy();
    expect(screen.queryByText("The audit log")).toBeNull();
  });

  it("sends a signed-out visitor to the sign-in page first", async () => {
    mockApi({ "GET /api/auth/me": jsonResponse(401, { detail: "Not signed in." }) });
    renderSecretPage();
    expect(await screen.findByRole("heading", { name: "Sign in page" })).toBeTruthy();
  });
});