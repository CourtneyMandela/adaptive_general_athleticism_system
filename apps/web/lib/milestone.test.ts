import { describe, expect, it } from "vitest";

import { milestone } from "./milestone";

describe("milestone copy", () => {
  it("describes real session containers without implying generated training", () => {
    expect(milestone.available.toLowerCase()).toContain("multi-item sessions");
    expect(milestone.available.toLowerCase()).toContain("session-level safety");
    expect(milestone.available.toLowerCase()).toContain("item-level progression");
    expect(milestone.deferred).toContain("verified seed data");
  });
});
