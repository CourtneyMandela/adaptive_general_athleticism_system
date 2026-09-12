import { describe, expect, it, vi } from "vitest";

import {
  AthleteDataExportRequestError,
  athleteDataExportFilename,
  fetchAthleteDataExport,
  type AthleteDataExport,
} from "./athlete-data-export";

const athleteId = "00000000-0000-4000-8000-000000000001";
const digest = `sha256:${"a".repeat(64)}`;
const payload: AthleteDataExport = {
  export_version: "athlete-data-export@1.1.0",
  generated_at: "2026-09-11T18:00:00Z",
  athlete_id: athleteId,
  tables: [
    {
      table_name: "athletes",
      primary_key_columns: ["id"],
      rows: [{ id: athleteId, display_name: "Fixture athlete" }],
    },
  ],
  external_references: [],
  manifest: {
    record_count: 1,
    table_counts: { athletes: 1 },
    content_digest: digest,
    scope: "athlete-owned rows and their non-athlete dependent rows",
    restore_status: "validated clean-store restore available through operator CLI",
  },
};

describe("athlete data export client", () => {
  it("downloads the authenticated owner export", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify(payload), { status: 200 }));

    await expect(fetchAthleteDataExport("http://localhost:8000/", athleteId, fetcher)).resolves.toEqual(
      payload,
    );
    expect(fetcher).toHaveBeenCalledWith(
      `http://localhost:8000/v1/athletes/${athleteId}/data-export`,
      {
        headers: {
          Accept: "application/json",
          Authorization: "Bearer dev.local-browser",
        },
      },
    );
    expect(athleteDataExportFilename(payload)).toBe(
      `agas-athlete-data-2026-09-11-${athleteId}.json`,
    );
  });

  it("preserves backend error detail", async () => {
    const fetcher = vi.fn(
      async () => new Response(JSON.stringify({ detail: "athlete does not exist" }), { status: 404 }),
    );

    await expect(fetchAthleteDataExport("http://localhost:8000", athleteId, fetcher)).rejects.toEqual(
      new AthleteDataExportRequestError("athlete does not exist", 404),
    );
  });

  it("rejects malformed or cross-athlete responses", async () => {
    const invalid = { ...payload, athlete_id: "00000000-0000-4000-8000-000000000002" };
    const fetcher = vi.fn(async () => new Response(JSON.stringify(invalid), { status: 200 }));

    await expect(fetchAthleteDataExport("http://localhost:8000", athleteId, fetcher)).rejects.toEqual(
      new AthleteDataExportRequestError("The server returned an invalid athlete export.", 502),
    );
  });
});
