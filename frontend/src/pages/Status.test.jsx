import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Status from "./Status.jsx";

function answerWith(status, body) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => body }),
  );
}

describe("Status page", () => {
  it("shows that the server is running when the health check succeeds", async () => {
    answerWith(200, { status: "ok" });
    render(<Status />);
    expect(screen.getByText("Checking the server...")).toBeTruthy();
    expect(await screen.findByRole("status")).toBeTruthy();
    expect(screen.getByText("The server is running.")).toBeTruthy();
  });

  it("shows a warning when the server cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(<Status />);
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("shows a warning when the server answers with an error", async () => {
    answerWith(500, { detail: "Internal server error" });
    render(<Status />);
    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});