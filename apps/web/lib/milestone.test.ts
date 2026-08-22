import { describe, expect, it } from "vitest";

import { milestone } from "./milestone";

describe("milestone copy", () => {
  it("describes the connected read slice without implying write workflows", () => {
    expect(milestone.available.toLowerCase()).toContain("persisted weekly sessions");
    expect(milestone.available.toLowerCase()).toContain("safety");
    expect(milestone.deferred).toContain("onboarding");
    expect(milestone.deferred).toContain("workout logging");
  });
});
