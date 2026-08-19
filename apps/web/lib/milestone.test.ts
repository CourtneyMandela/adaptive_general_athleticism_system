import { describe, expect, it } from "vitest";

import { milestone } from "./milestone";

describe("milestone copy", () => {
  it("describes review without implying automatic state updates or replanning", () => {
    expect(milestone.available.toLowerCase()).toContain("delivered-dose responses");
    expect(milestone.available.toLowerCase()).toContain("hypothesis review");
    expect(milestone.deferred).toContain("Capability updates");
    expect(milestone.deferred).toContain("replanning");
  });
});
