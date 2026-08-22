import { isUuid, type Confidence, type ProvenanceInput } from "./current-week";
import { authorizedHeaders } from "./identity";

export interface OnboardingEquipmentOption {
  equipment_id: string;
  name: string;
  category: string;
  capabilities: Record<string, unknown>;
}

export interface OnboardingEnvironmentInput {
  name: string;
  floorAreaM2: number | null;
  noiseConstraints: string | null;
  maxNoiseLevel: "low" | "moderate" | "high";
  outdoorAccess: boolean;
  equipmentIds: string[];
}

export interface AthleteOnboardingInput {
  displayName: string;
  goals: string[];
  preferredActivities: string[];
  dislikedActivities: string[];
  environments: OnboardingEnvironmentInput[];
  reliability: Confidence;
  reportedAt?: Date;
}

export interface AthleteOnboardingCommand {
  display_name: string;
  goals: string[];
  preferred_activities: string[];
  disliked_activities: string[];
  environments: Array<{
    name: string;
    floor_area_m2: number | null;
    noise_constraints: string | null;
    max_noise_level: "low" | "moderate" | "high";
    outdoor_access: boolean;
    equipment: Array<{
      equipment_id: string;
      capabilities: Record<string, never>;
      load_limits: Record<string, never>;
    }>;
  }>;
  reported_at: string;
  reliability: Confidence;
  provenance: ProvenanceInput;
}

export interface AthleteOnboardingResult {
  athlete: {
    id: string;
    display_name: string;
  };
  intake_observation: {
    id: string;
    observation_type: string;
  };
  environments: Array<{
    id: string;
    name: string;
  }>;
  equipment_availability: Array<{
    id: string;
    environment_id: string;
    equipment_id: string;
  }>;
}

export const onboardingProvenance: ProvenanceInput = {
  recorded_by: "unverified-athlete-user",
  source_system: "agas-web",
  ingestion_method: "onboarding-form",
};

export class OnboardingRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "OnboardingRequestError";
  }
}

function normalizeDistinct(values: string[], label: string): string[] {
  const normalized = values.map((value) => value.trim()).filter(Boolean);
  const keys = normalized.map((value) => value.toLocaleLowerCase());
  if (new Set(keys).size !== keys.length) {
    throw new Error(`${label} cannot contain duplicates.`);
  }
  return normalized;
}

export function buildAthleteOnboardingCommand(
  input: AthleteOnboardingInput,
): AthleteOnboardingCommand {
  const displayName = input.displayName.trim();
  if (!displayName) {
    throw new Error("Enter a display name.");
  }
  const goals = normalizeDistinct(input.goals, "Goals");
  if (goals.length === 0) {
    throw new Error("Enter at least one training goal.");
  }
  if (input.environments.length === 0) {
    throw new Error("Add at least one training environment.");
  }
  const preferred = normalizeDistinct(input.preferredActivities, "Preferred activities");
  const disliked = normalizeDistinct(input.dislikedActivities, "Disliked activities");
  const preferredKeys = new Set(preferred.map((value) => value.toLocaleLowerCase()));
  if (disliked.some((value) => preferredKeys.has(value.toLocaleLowerCase()))) {
    throw new Error("An activity cannot be both preferred and disliked.");
  }
  const environmentNames = input.environments.map((environment) => environment.name.trim());
  if (environmentNames.some((name) => !name)) {
    throw new Error("Every environment needs a name.");
  }
  if (
    new Set(environmentNames.map((name) => name.toLocaleLowerCase())).size !==
    environmentNames.length
  ) {
    throw new Error("Environment names cannot contain duplicates.");
  }

  const reportedAt = input.reportedAt ?? new Date();
  if (!Number.isFinite(reportedAt.valueOf())) {
    throw new Error("The reported time is invalid.");
  }

  return {
    display_name: displayName,
    goals,
    preferred_activities: preferred,
    disliked_activities: disliked,
    environments: input.environments.map((environment, index) => {
      const equipmentIds = normalizeDistinct(
        environment.equipmentIds,
        `Equipment in ${environmentNames[index]}`,
      );
      if (equipmentIds.some((equipmentId) => !isUuid(equipmentId))) {
        throw new Error(`Equipment in ${environmentNames[index]} contains an invalid selection.`);
      }
      if (environment.floorAreaM2 !== null && environment.floorAreaM2 <= 0) {
        throw new Error(`Floor area for ${environmentNames[index]} must be greater than zero.`);
      }
      return {
        name: environmentNames[index],
        floor_area_m2: environment.floorAreaM2,
        noise_constraints: environment.noiseConstraints?.trim() || null,
        max_noise_level: environment.maxNoiseLevel,
        outdoor_access: environment.outdoorAccess,
        equipment: equipmentIds.map((equipmentId) => ({
          equipment_id: equipmentId,
          capabilities: {},
          load_limits: {},
        })),
      };
    }),
    reported_at: reportedAt.toISOString(),
    reliability: input.reliability,
    provenance: onboardingProvenance,
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

export async function fetchOnboardingEquipment(
  apiBaseUrl: string,
  fetcher: typeof fetch = fetch,
): Promise<OnboardingEquipmentOption[]> {
  const response = await fetcher(`${apiBaseUrl.replace(/\/$/, "")}/v1/onboarding/equipment`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new OnboardingRequestError(
      await responseDetail(response, "Unable to load the equipment catalog."),
      response.status,
    );
  }
  return (await response.json()) as OnboardingEquipmentOption[];
}

export async function submitAthleteOnboarding(
  apiBaseUrl: string,
  command: AthleteOnboardingCommand,
  fetcher: typeof fetch = fetch,
): Promise<AthleteOnboardingResult> {
  const response = await fetcher(`${apiBaseUrl.replace(/\/$/, "")}/v1/onboarding/athletes`, {
    method: "POST",
    headers: authorizedHeaders({
      Accept: "application/json",
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(command),
  });
  if (!response.ok) {
    throw new OnboardingRequestError(
      await responseDetail(response, "Unable to create the athlete profile."),
      response.status,
    );
  }
  return (await response.json()) as AthleteOnboardingResult;
}
