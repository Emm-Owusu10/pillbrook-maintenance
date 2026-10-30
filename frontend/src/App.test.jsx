import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import App from "./App.jsx";

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App routing", () => {
  it("shows the home page at /", () => {
    renderAt("/");
    expect(screen.getByRole("heading", { name: "Report and track maintenance faults" })).toBeTruthy();
  });

  it("shows the status page at /status", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {}))); // never answers, so nothing changes after the test
    renderAt("/status");
    expect(screen.getByRole("heading", { name: "System status" })).toBeTruthy();
  });

  it("shows a page-not-found message for unknown addresses", () => {
    renderAt("/no-such-page");
    expect(screen.getByRole("heading", { name: "Page not found" })).toBeTruthy();
  });
});