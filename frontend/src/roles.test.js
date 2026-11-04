import { describe, expect, it } from "vitest";

import { roleLabel } from "./roles.js";

describe("roleLabel", () => {
  it("gives each role its everyday name", () => {
    expect(roleLabel("admin")).toBe("Administrator");
    expect(roleLabel("manager")).toBe("Facility Manager");
    expect(roleLabel("user")).toBe("Farm User");
    expect(roleLabel("something-else")).toBe("Unknown role");
  });
});