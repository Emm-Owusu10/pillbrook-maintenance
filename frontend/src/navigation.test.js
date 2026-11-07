import { describe, expect, it } from "vitest";

import { visibleNavItems } from "./navigation.js";

const ITEMS = [
  { to: "/account", label: "My account" },
  { to: "/requests", label: "All requests", permission: "view_all_requests" },
  { to: "/audit", label: "Audit log", permission: "view_audit_log" },
];

const canOnly = (...allowed) => (permission) => allowed.includes(permission);
const labels = (items) => items.map((item) => item.label);

describe("visibleNavItems", () => {
  it("shows nothing to someone who is not signed in", () => {
    expect(visibleNavItems(ITEMS, { status: "signedOut", can: canOnly("view_audit_log") })).toEqual([]);
    expect(visibleNavItems(ITEMS, { status: "loading", can: canOnly() })).toEqual([]);
  });

  it("shows items without a permission to any signed-in person", () => {
    expect(labels(visibleNavItems(ITEMS, { status: "signedIn", can: canOnly() }))).toEqual(["My account"]);
  });

  it("hides items whose permission is missing and shows those that are held", () => {
    const shown = visibleNavItems(ITEMS, { status: "signedIn", can: canOnly("view_audit_log") });
    expect(labels(shown)).toEqual(["My account", "Audit log"]);
  });

  it("keeps the order of the list", () => {
    const can = canOnly("view_all_requests", "view_audit_log");
    expect(labels(visibleNavItems(ITEMS, { status: "signedIn", can }))).toEqual([
      "My account",
      "All requests",
      "Audit log",
    ]);
  });
});