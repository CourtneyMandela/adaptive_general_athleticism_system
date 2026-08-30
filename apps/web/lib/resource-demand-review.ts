import { authorizedHeaders, reviewerDevelopmentAccessToken } from "./identity";

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export const movementPatterns = [
  "knee_dominant",
  "hip_hinge",
  "horizontal_push",
  "vertical_push",
  "horizontal_pull",
  "vertical_pull",
  "carry",
  "locomotion",
  "trunk_stability",
  "jump",
  "landing",
  "change_of_direction",
  "cyclic",
] as const;

export const loadingTypes = ["external_load", "bodyweight", "cyclic", "ballistic"] as const;
export const lateralities = ["bilateral", "unilateral", "alternating", "not_applicable"] as const;
export const loadabilities = ["limited", "moderate", "high"] as const;
export const velocityCharacteristics = ["controlled", "explosive", "continuous", "high_speed"] as const;
export const costLevels = ["low", "moderate", "high"] as const;
export const impactLevels = ["none", "low", "moderate", "high"] as const;

export type MovementPattern = (typeof movementPatterns)[number];
export type LoadingType = (typeof loadingTypes)[number];
export type Laterality = (typeof lateralities)[number];
export type Loadability = (typeof loadabilities)[number];
export type VelocityCharacteristic = (typeof velocityCharacteristics)[number];
export type CostLevel = (typeof costLevels)[number];
export type ImpactLevel = (typeof impactLevels)[number];

export interface ResourceDemandObservation {
  id: string;
  observed_at: string;
  observation_type: string;
  measurement: unknown;
  unit: string | null;
  source: string;
  reliability: string;
  context: Record<string, unknown>;
}

export interface ResourceDemandEvidenceClaim {
  id: string;
  claim: string;
  population: string;
  intervention: string;
  outcome: string;
  study_design: string;
  uncertainty: string;
  evidence_strength: string;
  athlete_applicability: string;
  applicability_notes: string;
  source_identifiers: Array<{ scheme: string; value: string }>;
  claim_version: string;
}

export interface ResourceDemandExercise {
  id: string;
  name: string;
  movement_patterns: MovementPattern[];
  primary_adaptation_ids: string[];
  secondary_adaptation_ids: string[];
  equipment_requirement_ids: string[];
  loading_type: LoadingType;
  laterality: Laterality;
  loadability: Loadability;
  skill_complexity: CostLevel;
  impact_level: ImpactLevel;
  velocity_characteristics: VelocityCharacteristic[];
  stability_demand: CostLevel;
  fatigue_cost: CostLevel;
  soreness_cost: CostLevel;
  requires_outdoor_access: boolean;
  minimum_floor_area_m2: number | null;
  contraindication_tags: string[];
}

export interface ResourceDemandPreparationProjection {
  strategy: {
    id: string;
    athlete_id: string;
    block_hypothesis: string;
    generated_at: string;
    next_review_at: string;
    rule_version: string;
  };
  projected_at: string;
  priorities: Array<{
    priority: {
      id: string;
      adaptation_id: string;
      state: "develop" | "maintain" | "expose" | "defer";
      score: number;
      rank: number;
      development_allocation: number;
      rationale: string[];
    };
    adaptation: {
      id: string;
      name: string;
      domain: string;
      preferred_stimuli: string[];
      valid_modalities: string[];
      dose_dimensions: string[];
      evidence_claim_ids: string[];
    };
    demand_history: Array<{
      resource_demand: {
        id: string;
        priority_state: string;
        minimum_weekly_minutes: number;
        target_weekly_minutes: number;
        sessions_per_week: number;
        rationale: string;
        demand_version: string;
      };
      stimulus_requirement: { id: string; rationale: string } | null;
      exercise_resolution: {
        id: string;
        status: "full" | "partial" | "infeasible";
        selected_exercise_id: string | null;
        unresolved_issues: Array<{ code: string; detail: string }>;
      } | null;
    }>;
  }>;
  source_observations: ResourceDemandObservation[];
  evidence_claims: ResourceDemandEvidenceClaim[];
  environments: Array<{
    environment: {
      id: string;
      name: string;
      space_constraints: Record<string, unknown>;
      noise_constraints: string | null;
      max_noise_level: CostLevel;
      outdoor_access: boolean;
    };
    snapshot: {
      captured_at: string;
      available_equipment: Array<{
        equipment_id: string;
        category: string;
        capabilities: Record<string, unknown>;
        load_limits: Record<string, unknown>;
      }>;
      source_availability_ids: string[];
      floor_area_m2: number | null;
      max_noise_level: CostLevel;
      outdoor_access: boolean;
    };
  }>;
  exercise_resolver_policies: Array<{
    id: string;
    policy_version: string;
    partial_match_threshold: number;
    full_match_threshold: number;
    max_ranked_candidates: number;
  }>;
  exercise_catalog: ResourceDemandExercise[];
  projection_version: string;
}

export interface StimulusSpecificationRequest {
  movement_patterns: MovementPattern[];
  allowed_loading_types: LoadingType[];
  allowed_lateralities: Laterality[];
  minimum_loadability: Loadability;
  required_velocity_characteristics: VelocityCharacteristic[];
  maximum_skill_complexity: CostLevel;
  maximum_impact_level: ImpactLevel;
  maximum_stability_demand: CostLevel;
  maximum_fatigue_cost: CostLevel;
  maximum_soreness_cost: CostLevel;
  requires_outdoor_access: boolean;
  minimum_floor_area_m2: number | null;
  contraindication_tags: string[];
  source_observation_ids: string[];
  evidence_claim_ids: string[];
  rationale: string;
}

interface ResourceDemandReviewFields {
  prepared_at: string;
  applicability_rationale: string;
  uncertainty: string;
  demand_rationale: string;
  demand_version: string;
}

export interface OperatorActiveResourceDemandRequest extends ResourceDemandReviewFields {
  mode: "active";
  environment_id: string;
  exercise_candidate_ids: string[];
  exercise_resolver_policy_id: string;
  stimulus_specification: StimulusSpecificationRequest;
  minimum_weekly_minutes: number;
  target_weekly_minutes: number;
  sessions_per_week: number;
}

export interface OperatorDeferredResourceDemandRequest extends ResourceDemandReviewFields {
  mode: "deferred";
  source_observation_ids: string[];
  evidence_claim_ids: string[];
}

export type OperatorResourceDemandRequest =
  | OperatorActiveResourceDemandRequest
  | OperatorDeferredResourceDemandRequest;

export interface ResourceDemandPreparationResult {
  stimulus_requirement: { id: string; rationale: string } | null;
  exercise_resolution: {
    id: string;
    status: "full" | "partial" | "infeasible";
    selected_exercise_id: string | null;
    unresolved_issues: Array<{ code: string; detail: string }>;
  } | null;
  resource_demand: {
    id: string;
    minimum_weekly_minutes: number;
    target_weekly_minutes: number;
    sessions_per_week: number;
    demand_version: string;
  };
  decision_record: {
    id: string;
    decision: string;
    reason: string;
    evidence: string[];
    uncertainty: string;
    decision_version: string;
  };
}

export class ResourceDemandReviewError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ResourceDemandReviewError";
  }
}

function normalizedBaseUrl(apiBaseUrl: string): string {
  return apiBaseUrl.replace(/\/$/, "");
}

async function responseError(response: Response): Promise<ResourceDemandReviewError> {
  let message = `Request failed with status ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) {
      message = body.detail;
    }
  } catch {
    // Preserve the status-based message for non-JSON failures.
  }
  return new ResourceDemandReviewError(message, response.status);
}

function assertUuid(value: string, label: string): void {
  if (!uuidPattern.test(value)) {
    throw new ResourceDemandReviewError(`${label} must be a UUID.`);
  }
}

function assertUniqueNonEmptyIds(values: string[], label: string): void {
  if (values.length === 0) {
    throw new ResourceDemandReviewError(`${label} requires at least one selection.`);
  }
  values.forEach((value, index) => assertUuid(value, `${label}[${index}]`));
  if (new Set(values).size !== values.length) {
    throw new ResourceDemandReviewError(`${label} must not contain duplicates.`);
  }
}

function assertControlledValue(
  value: string,
  allowedValues: readonly string[],
  label: string,
): void {
  if (!allowedValues.includes(value)) {
    throw new ResourceDemandReviewError(`${label} must be a supported controlled value.`);
  }
}

function assertUniqueControlledValues(
  values: string[],
  allowedValues: readonly string[],
  label: string,
  allowEmpty = false,
): void {
  if (!allowEmpty && values.length === 0) {
    throw new ResourceDemandReviewError(`${label} requires at least one selection.`);
  }
  values.forEach((value) => assertControlledValue(value, allowedValues, label));
  if (new Set(values).size !== values.length) {
    throw new ResourceDemandReviewError(`${label} must not contain duplicates.`);
  }
}

export function validateResourceDemandRequest(request: OperatorResourceDemandRequest): void {
  const unsafe = request as unknown as Record<string, unknown>;
  for (const protectedField of ["reviewed_by", "review_authority_assignment_id"]) {
    if (protectedField in unsafe) {
      throw new ResourceDemandReviewError(`${protectedField} is server-owned.`);
    }
  }
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(request.prepared_at)) {
    throw new ResourceDemandReviewError("prepared_at must include a timezone.");
  }
  for (const [value, label] of [
    [request.applicability_rationale, "Applicability rationale"],
    [request.uncertainty, "Uncertainty"],
    [request.demand_rationale, "Demand rationale"],
    [request.demand_version, "Demand version"],
  ] as const) {
    if (!value.trim()) throw new ResourceDemandReviewError(`${label} must not be blank.`);
  }
  if (request.mode === "deferred") {
    assertUniqueNonEmptyIds(request.source_observation_ids, "Observation provenance");
    assertUniqueNonEmptyIds(request.evidence_claim_ids, "Evidence provenance");
    return;
  }
  assertUuid(request.environment_id, "Environment");
  assertUuid(request.exercise_resolver_policy_id, "Resolver policy");
  assertUniqueNonEmptyIds(request.exercise_candidate_ids, "Exercise candidates");
  assertUniqueNonEmptyIds(
    request.stimulus_specification.source_observation_ids,
    "Observation provenance",
  );
  assertUniqueNonEmptyIds(
    request.stimulus_specification.evidence_claim_ids,
    "Evidence provenance",
  );
  const stimulus = request.stimulus_specification;
  assertUniqueControlledValues(stimulus.movement_patterns, movementPatterns, "Movement patterns");
  assertUniqueControlledValues(
    stimulus.allowed_loading_types,
    loadingTypes,
    "Allowed loading types",
  );
  assertUniqueControlledValues(
    stimulus.allowed_lateralities,
    lateralities,
    "Allowed lateralities",
  );
  assertUniqueControlledValues(
    stimulus.required_velocity_characteristics,
    velocityCharacteristics,
    "Required velocity characteristics",
    true,
  );
  assertControlledValue(stimulus.minimum_loadability, loadabilities, "Minimum loadability");
  assertControlledValue(stimulus.maximum_skill_complexity, costLevels, "Maximum skill complexity");
  assertControlledValue(stimulus.maximum_impact_level, impactLevels, "Maximum impact level");
  assertControlledValue(stimulus.maximum_stability_demand, costLevels, "Maximum stability demand");
  assertControlledValue(stimulus.maximum_fatigue_cost, costLevels, "Maximum fatigue cost");
  assertControlledValue(stimulus.maximum_soreness_cost, costLevels, "Maximum soreness cost");
  if (!stimulus.rationale.trim()) {
    throw new ResourceDemandReviewError("Stimulus rationale must not be blank.");
  }
  if (
    stimulus.minimum_floor_area_m2 !== null &&
    (!Number.isFinite(stimulus.minimum_floor_area_m2) || stimulus.minimum_floor_area_m2 <= 0)
  ) {
    throw new ResourceDemandReviewError(
      "Minimum floor area must be a positive number when supplied.",
    );
  }
  const normalizedContraindications = stimulus.contraindication_tags.map((tag) => tag.trim());
  if (normalizedContraindications.some((tag) => !tag)) {
    throw new ResourceDemandReviewError("Contraindication tags must not be blank.");
  }
  if (new Set(normalizedContraindications).size !== normalizedContraindications.length) {
    throw new ResourceDemandReviewError("Contraindication tags must not contain duplicates.");
  }
  const amounts = [
    [request.minimum_weekly_minutes, "Minimum weekly minutes"],
    [request.target_weekly_minutes, "Target weekly minutes"],
    [request.sessions_per_week, "Sessions per week"],
  ] as const;
  for (const [value, label] of amounts) {
    if (!Number.isInteger(value) || value <= 0) {
      throw new ResourceDemandReviewError(`${label} must be a positive integer.`);
    }
  }
  if (request.target_weekly_minutes < request.minimum_weekly_minutes) {
    throw new ResourceDemandReviewError("Target weekly minutes cannot be below the minimum.");
  }
  if (
    request.minimum_weekly_minutes % request.sessions_per_week !== 0 ||
    request.target_weekly_minutes % request.sessions_per_week !== 0
  ) {
    throw new ResourceDemandReviewError(
      "Minimum and target minutes must divide evenly across weekly sessions.",
    );
  }
}

export async function fetchResourceDemandPreparation(
  apiBaseUrl: string,
  strategyId: string,
  fetcher: typeof fetch = fetch,
): Promise<ResourceDemandPreparationProjection> {
  assertUuid(strategyId, "Strategy ID");
  const response = await fetcher(
    `${normalizedBaseUrl(apiBaseUrl)}/v1/operator/strategies/${strategyId}/resource-demand-preparation`,
    {
      headers: authorizedHeaders(
        { Accept: "application/json" },
        reviewerDevelopmentAccessToken,
      ),
    },
  );
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as ResourceDemandPreparationProjection;
}

export async function submitResourceDemand(
  apiBaseUrl: string,
  strategyId: string,
  priorityId: string,
  request: OperatorResourceDemandRequest,
  fetcher: typeof fetch = fetch,
): Promise<ResourceDemandPreparationResult> {
  assertUuid(strategyId, "Strategy ID");
  assertUuid(priorityId, "Priority ID");
  validateResourceDemandRequest(request);
  const response = await fetcher(
    `${normalizedBaseUrl(apiBaseUrl)}/v1/operator/strategies/${strategyId}/priorities/${priorityId}/resource-demands`,
    {
      method: "POST",
      headers: authorizedHeaders(
        { Accept: "application/json", "Content-Type": "application/json" },
        reviewerDevelopmentAccessToken,
      ),
      body: JSON.stringify(request),
    },
  );
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as ResourceDemandPreparationResult;
}
