import { type Confidence, type ProvenanceInput, isUuid } from "./current-week";
import { authorizedHeaders } from "./identity";

export type AssessmentWorkflowStatus =
  | "eligibility_required"
  | "eligibility_review_required"
  | "selection_blocked"
  | "eligibility_inactive"
  | "protocol_catalog_empty"
  | "environment_required"
  | "ready_to_start"
  | "selection_deferred"
  | "result_entry_ready"
  | "run_blocked"
  | "complete";

export type AssessmentResultStatus =
  | "completed"
  | "ready"
  | "not_selected"
  | "protocol_unavailable"
  | "eligibility_unavailable";

export interface AssessmentDecisionProjection {
  selection_id: string;
  decision: "selected" | "deferred" | "excluded";
  reason_codes: string[];
  rationale: string[];
  assessment_definition_id: string;
  assessment_definition_review_id: string | null;
  name: string;
  domain: string;
  intensity: string;
  unit_or_scale: string;
  protocol_version: string;
  protocol_instructions: string[];
  result_entry_instructions: string;
  applicability_notes: string;
  uncertainty: string;
  evidence_claim_ids: string[];
  review_version: string;
  result_status: AssessmentResultStatus;
  result: {
    performance_id: string;
    result_observation_id: string;
    performed_at: string;
    measurement: unknown;
    unit: string | null;
    reliability: Confidence;
    provenance: Record<string, unknown>;
    rule_version: string;
  } | null;
}

export interface AssessmentWorkflowProjection {
  athlete_id: string;
  athlete_display_name: string;
  as_of: string;
  status: AssessmentWorkflowStatus;
  message: string;
  can_start_run: boolean;
  can_record_results: boolean;
  approved_self_administered_protocol_count: number;
  eligibility: {
    eligibility_review_id: string;
    outcome: "selection_allowed" | "selection_blocked" | "review_required";
    reviewed_at: string;
    valid_until: string;
    rule_version: string;
  } | null;
  environments: Array<{ environment_id: string; name: string }>;
  latest_run: {
    run_id: string;
    environment_id: string;
    environment_name: string;
    evaluated_at: string;
    rule_version: string;
    decisions: AssessmentDecisionProjection[];
  } | null;
}

export interface AssessmentRunInput {
  environmentId: string;
  bodyMassKg: number | null;
  trainingAgeMonthsByDomain: Record<string, number | null>;
  exerciseSkillTags: string[];
  recentExposureTags: string[];
  reliability: Confidence;
  evaluatedAt?: Date;
}

export interface AssessmentRunCommand {
  environment_id: string;
  body_mass_kg: number | null;
  training_age_months_by_domain: Record<string, number>;
  exercise_skill_tags: string[];
  recent_exposure_tags: string[];
  evaluated_at: string;
  reliability: Confidence;
  provenance: ProvenanceInput;
}

export const assessmentProvenance: ProvenanceInput = {
  recorded_by: "unverified-athlete-user",
  source_system: "agas-web",
  ingestion_method: "assessment-context-form",
};

export class AssessmentRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "AssessmentRequestError";
  }
}

function normalizedTags(values: string[], label: string): string[] {
  const normalized = values.map((value) => value.trim()).filter(Boolean);
  const keys = normalized.map((value) => value.toLocaleLowerCase());
  if (new Set(keys).size !== keys.length) {
    throw new Error(`${label} cannot contain duplicates.`);
  }
  return normalized;
}

export function buildAssessmentRunCommand(input: AssessmentRunInput): AssessmentRunCommand {
  if (!isUuid(input.environmentId)) {
    throw new Error("Choose a persisted assessment environment.");
  }
  if (input.bodyMassKg !== null && (!Number.isFinite(input.bodyMassKg) || input.bodyMassKg <= 0)) {
    throw new Error("Body mass must be greater than zero when reported.");
  }
  const trainingHistory = Object.fromEntries(
    Object.entries(input.trainingAgeMonthsByDomain)
      .filter((entry): entry is [string, number] => entry[1] !== null)
      .map(([domain, months]) => {
        if (!Number.isInteger(months) || months < 0) {
          throw new Error("Training history must use whole, non-negative months.");
        }
        return [domain, months];
      }),
  );
  const evaluatedAt = input.evaluatedAt ?? new Date();
  if (!Number.isFinite(evaluatedAt.valueOf())) {
    throw new Error("The assessment time is invalid.");
  }
  return {
    environment_id: input.environmentId,
    body_mass_kg: input.bodyMassKg,
    training_age_months_by_domain: trainingHistory,
    exercise_skill_tags: normalizedTags(input.exerciseSkillTags, "Skill tags"),
    recent_exposure_tags: normalizedTags(input.recentExposureTags, "Exposure tags"),
    evaluated_at: evaluatedAt.toISOString(),
    reliability: input.reliability,
    provenance: assessmentProvenance,
  };
}

async function responseDetail(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : fallback;
  } catch {
    return fallback;
  }
}

export async function fetchAssessmentWorkflow(
  apiBaseUrl: string,
  athleteId: string,
  fetcher: typeof fetch = fetch,
): Promise<AssessmentWorkflowProjection> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/athletes/${athleteId}/assessment-workflow`,
    { headers: authorizedHeaders({ Accept: "application/json" }) },
  );
  if (!response.ok) {
    throw new AssessmentRequestError(
      await responseDetail(response, "Unable to load assessment status."),
      response.status,
    );
  }
  return (await response.json()) as AssessmentWorkflowProjection;
}

export async function submitAssessmentRun(
  apiBaseUrl: string,
  athleteId: string,
  command: AssessmentRunCommand,
  fetcher: typeof fetch = fetch,
): Promise<unknown> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/athletes/${athleteId}/assessment-runs`,
    {
      method: "POST",
      headers: authorizedHeaders({
        Accept: "application/json",
        "Content-Type": "application/json",
      }),
      body: JSON.stringify(command),
    },
  );
  if (!response.ok) {
    throw new AssessmentRequestError(
      await responseDetail(response, "Unable to create assessment selection."),
      response.status,
    );
  }
  return response.json();
}
