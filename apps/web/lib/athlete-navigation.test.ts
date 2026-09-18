import { describe, expect, it } from "vitest";

import { athleteHomeHref, athleteReviewHref, athleteWeekHref } from "./athlete-navigation";

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

  it("opens an athlete's exact persisted week without losing either query value", () => {
    expect(athleteWeekHref(athleteId, "2026-09-14")).toBe(
      `/?athleteId=${athleteId}&asOf=2026-09-14`,
    );
  });

  it("does not propagate malformed athlete or date values into a week link", () => {
    expect(athleteWeekHref("not-an-id", "not-a-date")).toBe("/");
    expect(athleteWeekHref(null, "2026-09-14")).toBe("/?asOf=2026-09-14");
  });
});
