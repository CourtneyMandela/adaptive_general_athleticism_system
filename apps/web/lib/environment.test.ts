import { describe, expect, it, vi } from "vitest";

import {
  buildEnvironmentFloorAreaReportCommand,
  buildEquipmentStateReportCommand,
  fetchAthleteEnvironments,
  submitEnvironmentFloorAreaReport,
  submitEquipmentStateReport,
  type AthleteEnvironmentProjection,
} from "./environment";

const athleteId = "00000000-0000-4000-8000-000000000001";
const environmentId = "00000000-0000-4000-8000-000000000002";
const equipmentId = "00000000-0000-4000-8000-000000000003";

describe("environment client", () => {
  it("builds a partial temporal report without implying omitted equipment state", () => {
    const command = buildEquipmentStateReportCommand({
      changes: [
        {
          equipmentId,
          isAvailable: false,
          effectiveFrom: new Date("2026-09-01T14:00:00Z"),
          effectiveUntil: new Date("2026-09-08T14:00:00Z"),
          reason: "Travel week",
        },
      ],
      reliability: "moderate",
      reportReason: " Hotel equipment confirmation ",
      reportedAt: new Date("2026-08-28T18:00:00Z"),
    });

    expect(command).toEqual({
      changes: [
        {
          equipment_id: equipmentId,
          is_available: false,
          effective_from: "2026-09-01T14:00:00.000Z",
          effective_until: "2026-09-08T14:00:00.000Z",
          capabilities: {},
          load_limits: {},
          reason: "Travel week",
        },
      ],
      reported_at: "2026-08-28T18:00:00.000Z",
      reliability: "moderate",
      provenance: {
        recorded_by: "unverified-athlete-user",
        source_system: "agas-web",
        ingestion_method: "equipment-state-form",
      },
      report_reason: "Hotel equipment confirmation",
    });
  });

  it("rejects empty, duplicate, and invalid temporal changes", () => {
    expect(() =>
      buildEquipmentStateReportCommand({
        changes: [],
        reliability: "low",
        reportReason: "Travel",
      }),
    ).toThrow("at least one");
    const change = {
      equipmentId,
      isAvailable: true,
      effectiveFrom: new Date("2026-09-01T14:00:00Z"),
      effectiveUntil: null,
      reason: null,
    };
    expect(() =>
      buildEquipmentStateReportCommand({
        changes: [change, change],
        reliability: "low",
        reportReason: "Travel",
      }),
    ).toThrow("duplicates");
    expect(() =>
      buildEquipmentStateReportCommand({
        changes: [{ ...change, effectiveUntil: change.effectiveFrom }],
        reliability: "low",
        reportReason: "Travel",
      }),
    ).toThrow("end after");
  });

  it("loads and submits owned environment state with authorization", async () => {
    const projection: AthleteEnvironmentProjection = {
      athlete_id: athleteId,
      as_of: "2026-08-28T18:00:00Z",
      environments: [],
      projection_version: "athlete-environment-state@1.0.0",
    };
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(JSON.stringify(projection), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ observation: { id: equipmentId }, availability_events: [] }),
          { status: 201 },
        ),
      );
    await expect(fetchAthleteEnvironments("http://localhost:8000/", athleteId, fetcher)).resolves.toEqual(
      projection,
    );
    const command = buildEquipmentStateReportCommand({
      changes: [
        {
          equipmentId,
          isAvailable: true,
          effectiveFrom: new Date("2026-09-01T14:00:00Z"),
          effectiveUntil: null,
          reason: null,
        },
      ],
      reliability: "high",
      reportReason: "Equipment added",
    });
    await submitEquipmentStateReport(
      "http://localhost:8000",
      athleteId,
      environmentId,
      command,
      fetcher,
    );
    expect(fetcher.mock.calls[0][1]).toEqual({
      headers: { Accept: "application/json", Authorization: "Bearer dev.local-browser" },
    });
    expect(fetcher.mock.calls[1][0]).toContain(`/environments/${environmentId}/equipment-reports`);
    expect(JSON.parse(fetcher.mock.calls[1][1]!.body as string)).toEqual(command);
  });

  it("builds and submits an append-only usable-floor-area report", async () => {
    const command = buildEnvironmentFloorAreaReportCommand({
      floorAreaM2: 4.5,
      reliability: "moderate",
      reportReason: " Measured clear living-room space ",
      effectiveFrom: new Date("2026-09-10T18:00:00Z"),
      reportedAt: new Date("2026-09-10T18:01:00Z"),
    });
    expect(command).toMatchObject({
      floor_area_m2: 4.5,
      effective_from: "2026-09-10T18:00:00.000Z",
      report_reason: "Measured clear living-room space",
      provenance: { ingestion_method: "environment-floor-area-form" },
    });
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ observation: { id: equipmentId } }), { status: 201 }),
    );

    await submitEnvironmentFloorAreaReport(
      "http://localhost:8000",
      athleteId,
      environmentId,
      command,
      fetcher,
    );

    expect(fetcher.mock.calls[0][0]).toContain("floor-area-reports");
    expect(JSON.parse(fetcher.mock.calls[0][1]!.body as string)).toEqual(command);
  });
});
