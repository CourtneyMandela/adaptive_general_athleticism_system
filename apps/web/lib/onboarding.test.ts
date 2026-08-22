import { describe, expect, it, vi } from "vitest";

import {
  buildAthleteOnboardingCommand,
  fetchOnboardingEquipment,
  OnboardingRequestError,
  submitAthleteOnboarding,
} from "./onboarding";

const equipmentId = "00000000-0000-4000-8000-000000000001";

describe("governed onboarding client", () => {
  it("builds a normalized, timestamped user report without inferred state", () => {
    const command = buildAthleteOnboardingCommand({
      displayName: "  Example Athlete ",
      goals: [" General athleticism "],
      preferredActivities: ["Hiking"],
      dislikedActivities: ["Treadmill"],
      environments: [
        {
          name: " Home ",
          floorAreaM2: 15,
          noiseConstraints: " Quiet after 8 PM ",
          maxNoiseLevel: "low",
          outdoorAccess: true,
          equipmentIds: [equipmentId],
        },
      ],
      reliability: "moderate",
      reportedAt: new Date("2026-08-22T18:00:00Z"),
    });

    expect(command).toEqual({
      display_name: "Example Athlete",
      goals: ["General athleticism"],
      preferred_activities: ["Hiking"],
      disliked_activities: ["Treadmill"],
      environments: [
        {
          name: "Home",
          floor_area_m2: 15,
          noise_constraints: "Quiet after 8 PM",
          max_noise_level: "low",
          outdoor_access: true,
          equipment: [{ equipment_id: equipmentId, capabilities: {}, load_limits: {} }],
        },
      ],
      reported_at: "2026-08-22T18:00:00.000Z",
      reliability: "moderate",
      provenance: {
        recorded_by: "unverified-athlete-user",
        source_system: "agas-web",
        ingestion_method: "onboarding-form",
      },
    });
    expect(command).not.toHaveProperty("capability_estimates");
    expect(command).not.toHaveProperty("safety_policy_id");
  });

  it("rejects ambiguous identity, preference, environment, and equipment inputs", () => {
    const base = {
      displayName: "Example",
      goals: ["Move well"],
      preferredActivities: ["Hiking"],
      dislikedActivities: ["Running"],
      environments: [
        {
          name: "Home",
          floorAreaM2: null,
          noiseConstraints: null,
          maxNoiseLevel: "moderate" as const,
          outdoorAccess: false,
          equipmentIds: [equipmentId],
        },
      ],
      reliability: "moderate" as const,
    };
    expect(() => buildAthleteOnboardingCommand({ ...base, displayName: " " })).toThrow(
      "display name",
    );
    expect(() =>
      buildAthleteOnboardingCommand({ ...base, dislikedActivities: ["hiking"] }),
    ).toThrow("both preferred and disliked");
    expect(() =>
      buildAthleteOnboardingCommand({
        ...base,
        environments: [...base.environments, { ...base.environments[0], name: "home" }],
      }),
    ).toThrow("Environment names");
    expect(() =>
      buildAthleteOnboardingCommand({
        ...base,
        environments: [{ ...base.environments[0], equipmentIds: ["not-an-id"] }],
      }),
    ).toThrow("invalid selection");
  });

  it("loads controlled equipment and posts the exact onboarding command", async () => {
    const fetcher = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            { equipment_id: equipmentId, name: "Open floor", category: "space", capabilities: {} },
          ]),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            athlete: { id: equipmentId, display_name: "Example" },
            intake_observation: { id: equipmentId, observation_type: "onboarding_profile_environment_report" },
            environments: [],
            equipment_availability: [],
          }),
          { status: 201 },
        ),
      );
    const command = buildAthleteOnboardingCommand({
      displayName: "Example",
      goals: ["Move well"],
      preferredActivities: [],
      dislikedActivities: [],
      environments: [{
        name: "Home",
        floorAreaM2: null,
        noiseConstraints: null,
        maxNoiseLevel: "moderate",
        outdoorAccess: false,
        equipmentIds: [],
      }],
      reliability: "moderate",
      reportedAt: new Date("2026-08-22T18:00:00Z"),
    });

    await expect(fetchOnboardingEquipment("http://localhost:8000/", fetcher)).resolves.toHaveLength(1);
    await expect(submitAthleteOnboarding("http://localhost:8000/", command, fetcher)).resolves.toMatchObject({
      athlete: { display_name: "Example" },
    });
    expect(fetcher.mock.calls[0][0]).toBe("http://localhost:8000/v1/onboarding/equipment");
    expect(fetcher.mock.calls[1][0]).toBe("http://localhost:8000/v1/onboarding/athletes");
    expect(fetcher.mock.calls[1][1]).toMatchObject({ method: "POST" });
    expect(JSON.parse(fetcher.mock.calls[1][1]!.body as string)).toEqual(command);
  });

  it("preserves server validation details", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ detail: "equipment selection does not exist" }), { status: 404 }),
    );
    await expect(fetchOnboardingEquipment("http://localhost:8000", fetcher)).rejects.toEqual(
      new OnboardingRequestError("equipment selection does not exist", 404),
    );
  });
});
