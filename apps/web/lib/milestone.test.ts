import { describe, expect, it } from "vitest";

import { milestone } from "./milestone";

describe("milestone copy", () => {
  it("describes controlled resolution without implying generated training", () => {
    expect(milestone.available.toLowerCase()).toContain("validated small seed catalog");
    expect(milestone.available.toLowerCase()).toContain("partial");
    expect(milestone.deferred).toContain("automatic workout generation");
    expect(milestone.deferred).toContain("Production-approved");
  });
});
