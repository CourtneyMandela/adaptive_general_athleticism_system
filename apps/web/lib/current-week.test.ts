import { describe, expect, it, vi } from "vitest";

import {
  CurrentWeekRequestError,
  fetchCurrentWeek,
  formatDose,
  isUuid,
  sessionStatusLabel,
  shiftIsoDate,
  type PrescriptionProjection,
} from "./current-week";

const prescription: PrescriptionProjection = {
  order_index: 1,
  section: "primary",
  prescription_id: "00000000-0000-4000-8000-000000000001",
  exercise_id: "00000000-0000-4000-8000-000000000002",
  exercise_name: "Fixture squat",
  adaptation_id: "00000000-0000-4000-8000-000000000003",
  adaptation_name: "Maximum strength",
  reason_for_inclusion: "Fixture reason",
  sets: 3,
  repetitions_per_set: 5,
  duration_seconds: null,
  intensity_targets: ["RPE 6-8"],
  rest_seconds: 120,
  adherence: null,
  progression: null,
};

describe("current-week presentation", () => {
  it("formats prescribed repetitions and duration without changing the dose", () => {
    expect(formatDose(prescription)).toBe("3 × 5");
    expect(
      formatDose({ ...prescription, sets: 1, repetitions_per_set: null, duration_seconds: 1080 }),
    ).toBe("1 × 18 min");
  });

  it("moves the requested date by a week and validates athlete identifiers", () => {
    expect(shiftIsoDate("2026-08-24", 7)).toBe("2026-08-31");
    expect(isUuid(prescription.prescription_id)).toBe(true);
    expect(isUuid("not-an-athlete-id")).toBe(false);
  });

  it("uses explicit, safety-aware status labels", () => {
    expect(sessionStatusLabel("cleared")).toBe("Safety cleared");
    expect(sessionStatusLabel("needs_attention")).toBe("Needs attention");
    expect(sessionStatusLabel("stopped_safety")).toBe("Stopped for safety");
  });

  it("requests the dated projection and preserves API errors", async () => {
    const success = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          athlete_id: prescription.adaptation_id,
          athlete_display_name: "Fixture athlete",
          as_of: "2026-08-24",
          week: null,
        }),
        { status: 200 },
      ),
    );
    await expect(
      fetchCurrentWeek("http://localhost:8000/", prescription.adaptation_id, "2026-08-24", success),
    ).resolves.toMatchObject({ athlete_display_name: "Fixture athlete", week: null });
    expect(success).toHaveBeenCalledWith(
      `http://localhost:8000/v1/athletes/${prescription.adaptation_id}/current-week?on=2026-08-24`,
      { headers: { Accept: "application/json" } },
    );

    const failure = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify({ detail: "athlete does not exist" }), { status: 404 }));
    await expect(
      fetchCurrentWeek("http://localhost:8000", prescription.adaptation_id, "2026-08-24", failure),
    ).rejects.toEqual(new CurrentWeekRequestError("athlete does not exist", 404));
  });
});
