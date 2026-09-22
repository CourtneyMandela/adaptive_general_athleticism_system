import { describe, expect, it } from "vitest";

import { formatRestTime, remainingRestSeconds } from "./rest-timer";

describe("local rest timer", () => {
  it("rounds a running deadline up without producing negative time", () => {
    expect(remainingRestSeconds(121_000, 1_001)).toBe(120);
    expect(remainingRestSeconds(1_000, 1_001)).toBe(0);
    expect(remainingRestSeconds(Number.NaN, 0)).toBe(0);
  });

  it("formats prescribed seconds as a readable countdown", () => {
    expect(formatRestTime(120)).toBe("2:00");
    expect(formatRestTime(65)).toBe("1:05");
    expect(formatRestTime(-1)).toBe("0:00");
  });
});
