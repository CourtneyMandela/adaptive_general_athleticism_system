import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AthleteDemographicsRequestError,
  fetchAthleteDemographics,
  submitDateOfBirthReport,
} from "./athlete-demographics";

const athleteId = "00000000-0000-4000-8000-000000000001";

describe("athlete demographics client", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("loads the provenance-bearing current projection", async () => {
    const projection = {
      athlete_id: athleteId,
      as_of: "2026-09-09T12:00:00Z",
      date_of_birth: "1990-01-03",
      age_years: 36,
      source_observation_id: "00000000-0000-4000-8000-000000000002",
      source_kind: "reported_observation",
      report_count: 2,
      message: "Earlier reports remain in history.",
      projection_version: "athlete-demographics-projection@1.0.0",
    };
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify(projection), { status: 200 }));

    await expect(
      fetchAthleteDemographics("http://localhost:8000/", athleteId, fetcher),
    ).resolves.toEqual(projection);
    expect(fetcher).toHaveBeenCalledWith(
      `http://localhost:8000/v1/athletes/${athleteId}/demographics`,
      {
        headers: {
          Accept: "application/json",
          Authorization: "Bearer dev.local-browser",
        },
      },
    );
  });

  it("submits only an attested date-of-birth observation", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-09T12:34:56Z"));
    const result = { observation_id: "report", created: true };
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify(result), { status: 201 }));

    await expect(
      submitDateOfBirthReport("http://localhost:8000", athleteId, "1990-01-03", fetcher),
    ).resolves.toEqual(result);

    const [, options] = fetcher.mock.calls[0] ?? [];
    expect(options).toMatchObject({
      method: "POST",
      headers: {
        Accept: "application/json",
        Authorization: "Bearer dev.local-browser",
        "Content-Type": "application/json",
      },
    });
    const body = JSON.parse(String(options?.body)) as Record<string, unknown>;
    expect(body).toMatchObject({
      date_of_birth: "1990-01-03",
      reported_at: "2026-09-09T12:34:56.000Z",
      date_of_birth_confirmed: true,
    });
    expect(body.report_id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
  });

  it("preserves API errors", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify({ detail: "athlete does not exist" }), { status: 404 }));

    await expect(
      fetchAthleteDemographics("http://localhost:8000", athleteId, fetcher),
    ).rejects.toEqual(new AthleteDemographicsRequestError("athlete does not exist", 404));
  });
});
