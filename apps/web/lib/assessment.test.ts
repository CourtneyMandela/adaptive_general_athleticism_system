import { describe, expect, it, vi } from "vitest";

import {
  AssessmentRequestError,
  buildAssessmentResultCommand,
  buildAssessmentRunCommand,
  fetchAssessmentWorkflow,
  submitAssessmentCapabilityEstimate,
  submitAssessmentRun,
  submitAssessmentResult,
  type AssessmentDecisionProjection,
} from "./assessment";

const athleteId = "00000000-0000-4000-8000-000000000001";
const environmentId = "00000000-0000-4000-8000-000000000002";
const decision: AssessmentDecisionProjection = {
  selection_id: "00000000-0000-4000-8000-000000000003",
  decision: "selected",
  reason_codes: ["eligible"],
  rationale: ["Fixture eligibility."],
  assessment_definition_id: "00000000-0000-4000-8000-000000000004",
  assessment_definition_review_id: "00000000-0000-4000-8000-000000000005",
  name: "Fixture assessment",
  domain: "aerobic_capacity",
  intensity: "low",
  unit_or_scale: "fixture_unit",
  protocol_version: "fixture@1.0.0",
  protocol_instructions: ["Follow fixture instructions."],
  result_entry_instructions: "Enter fixture result.",
  measurement_schema: {
    measurement_type: "number",
    label: "Fixture value",
    minimum: 0,
    maximum: 10,
    step: 0.5,
    allowed_values: [],
    measurement_schema_version: "fixture-schema@1.0.0",
  },
  applicability_notes: "Fixture only.",
  uncertainty: "Not operational.",
  evidence_claim_ids: ["00000000-0000-4000-8000-000000000006"],
  review_version: "fixture-review@1.0.0",
  result_status: "ready",
  result: null,
};

describe("assessment workflow client", () => {
  it("builds a narrow non-medical selection command with explicit provenance", () => {
    const command = buildAssessmentRunCommand({
      environmentId,
      bodyMassKg: 80.5,
      trainingAgeMonthsByDomain: {
        aerobic_capacity: 12,
        maximal_strength: null,
      },
      exerciseSkillTags: [" cycle ", "balance"],
      recentExposureTags: ["hiking"],
      reliability: "moderate",
      evaluatedAt: new Date("2026-08-27T12:00:00Z"),
    });

    expect(command).toEqual({
      environment_id: environmentId,
      body_mass_kg: 80.5,
      training_age_months_by_domain: { aerobic_capacity: 12 },
      exercise_skill_tags: ["cycle", "balance"],
      recent_exposure_tags: ["hiking"],
      evaluated_at: "2026-08-27T12:00:00.000Z",
      reliability: "moderate",
      provenance: {
        recorded_by: "unverified-athlete-user",
        source_system: "agas-web",
        ingestion_method: "assessment-context-form",
      },
    });
    expect(command).not.toHaveProperty("health_screening_completed");
    expect(command).not.toHaveProperty("equipment_categories");
  });

  it("rejects invalid history, body mass, and duplicate tags before transport", () => {
    const base = {
      environmentId,
      bodyMassKg: null,
      trainingAgeMonthsByDomain: {},
      exerciseSkillTags: [],
      recentExposureTags: [],
      reliability: "low" as const,
    };
    expect(() => buildAssessmentRunCommand({ ...base, bodyMassKg: 0 })).toThrow("greater than zero");
    expect(() =>
      buildAssessmentRunCommand({
        ...base,
        trainingAgeMonthsByDomain: { aerobic_capacity: 1.5 },
      }),
    ).toThrow("whole, non-negative months");
    expect(() =>
      buildAssessmentRunCommand({ ...base, exerciseSkillTags: ["Cycle", "cycle"] }),
    ).toThrow("duplicates");
  });

  it("builds only results allowed by the reviewed measurement schema", () => {
    expect(
      buildAssessmentResultCommand(
        decision,
        "7.5",
        "moderate",
        new Date("2026-08-27T12:30:00Z"),
      ),
    ).toEqual({
      performed_at: "2026-08-27T12:30:00.000Z",
      measurement: 7.5,
      unit: "fixture_unit",
      reliability: "moderate",
      provenance: {
        recorded_by: "unverified-athlete-user",
        source_system: "agas-web",
        ingestion_method: "assessment-result-form",
      },
    });
    expect(() => buildAssessmentResultCommand(decision, "7.3", "low")).toThrow("increments");
    expect(() => buildAssessmentResultCommand(decision, "11", "low")).toThrow("at most");
    const categorical = {
      ...decision,
      measurement_schema: {
        measurement_type: "category" as const,
        label: "Fixture category",
        minimum: null,
        maximum: null,
        step: null,
        allowed_values: ["complete", "incomplete"],
        measurement_schema_version: "fixture-category@1.0.0",
      },
    };
    expect(buildAssessmentResultCommand(categorical, "complete", "high").measurement).toBe(
      "complete",
    );
    expect(() => buildAssessmentResultCommand(categorical, "other", "high")).toThrow("allowed");
  });

  it("loads the owned workflow with a development bearer", async () => {
    const projection = {
      athlete_id: athleteId,
      athlete_display_name: "Fixture",
      as_of: "2026-08-27T12:00:00Z",
      status: "protocol_catalog_empty",
      message: "No approved protocol.",
      can_start_run: false,
      can_record_results: false,
      approved_self_administered_protocol_count: 0,
      due_protocol_count: 0,
      next_reassessment_at: null,
      reassessment_rule_version: "assessment-reassessment-schedule@1.0.0",
      eligibility: null,
      environments: [],
      latest_run: null,
    };
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(projection), { status: 200 }),
    );

    await expect(fetchAssessmentWorkflow("http://localhost:8000/", athleteId, fetcher)).resolves.toEqual(
      projection,
    );
    expect(fetcher).toHaveBeenCalledWith(
      `http://localhost:8000/v1/athletes/${athleteId}/assessment-workflow`,
      {
        headers: {
          Accept: "application/json",
          Authorization: "Bearer dev.local-browser",
        },
      },
    );
  });

  it("posts governed selection and preserves API conflict details", async () => {
    const command = buildAssessmentRunCommand({
      environmentId,
      bodyMassKg: null,
      trainingAgeMonthsByDomain: {},
      exerciseSkillTags: [],
      recentExposureTags: [],
      reliability: "unknown",
      evaluatedAt: new Date("2026-08-27T12:00:00Z"),
    });
    const success = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ run: { id: athleteId } }), { status: 201 }),
    );
    await submitAssessmentRun("http://localhost:8000", athleteId, command, success);
    expect(success.mock.calls[0]?.[1]).toMatchObject({
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        Authorization: "Bearer dev.local-browser",
      },
      body: JSON.stringify(command),
    });

    const conflict = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ detail: "eligibility is not active" }), { status: 409 }),
    );
    await expect(
      submitAssessmentRun("http://localhost:8000", athleteId, command, conflict),
    ).rejects.toEqual(new AssessmentRequestError("eligibility is not active", 409));
  });

  it("posts a schema-governed result beneath its exact run and selection", async () => {
    const command = buildAssessmentResultCommand(
      decision,
      "5",
      "moderate",
      new Date("2026-08-27T12:30:00Z"),
    );
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ performance: { id: athleteId } }), { status: 201 }),
    );
    await submitAssessmentResult(
      "http://localhost:8000",
      athleteId,
      environmentId,
      decision.selection_id,
      command,
      fetcher,
    );
    expect(fetcher.mock.calls[0]?.[0]).toBe(
      `http://localhost:8000/v1/athletes/${athleteId}/assessment-runs/${environmentId}` +
        `/selections/${decision.selection_id}/result`,
    );
    expect(fetcher.mock.calls[0]?.[1]).toMatchObject({
      method: "POST",
      body: JSON.stringify(command),
    });
  });

  it("requests server-governed capability interpretation without sending a formula", async () => {
    const performanceId = "00000000-0000-4000-8000-000000000007";
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ estimate: { id: performanceId } }), { status: 201 }),
    );

    await submitAssessmentCapabilityEstimate(
      "http://localhost:8000/",
      athleteId,
      performanceId,
      fetcher,
    );

    expect(fetcher).toHaveBeenCalledWith(
      `http://localhost:8000/v1/athletes/${athleteId}` +
        `/assessment-performances/${performanceId}/capability-estimate`,
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          Authorization: "Bearer dev.local-browser",
        },
      },
    );
  });
});
