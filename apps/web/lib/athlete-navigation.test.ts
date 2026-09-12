import { describe, expect, it } from "vitest";

import { athleteHomeHref, athleteReviewHref } from "./athlete-navigation";

const athleteId = "0fe4fa6f-d3de-49f8-8d95-239854fb0ecb";

describe("athlete-aware navigation", () => {
  it("preserves a valid athlete when entering a review route", () => {
    expect(athleteReviewHref("/review/assessments", athleteId)).toBe(
      `/review/assessments?athleteId=${athleteId}`,
    );
  });

  it("preserves a valid athlete and anchor when returning home", () => {
    expect(athleteHomeHref(athleteId, "assessment-title")).toBe(
      `/?athleteId=${athleteId}#assessment-title`,
    );
  });

  it("does not propagate malformed athlete identifiers", () => {
    expect(athleteReviewHref("/review/assessments", "not-an-id")).toBe(
      "/review/assessments",
    );
    expect(athleteHomeHref("not-an-id", "assessment-title")).toBe(
      "/#assessment-title",
    );
  });
});
