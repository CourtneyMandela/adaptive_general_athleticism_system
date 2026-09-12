import { authorizedHeaders } from "./identity";

export type OwnerAlphaAccessStatus =
  | "not_configured"
  | "identity_not_allowlisted"
  | "account_required"
  | "athlete_required"
  | "revoked"
  | "eligible"
  | "active";

export interface OwnerAlphaRoleProjection {
  role: "assessment_reviewer" | "planning_reviewer";
  status: "active" | "revoked" | null;
  assignment_id: string | null;
}

export interface OwnerAlphaAccessProjection {
  access_version: string;
  status: OwnerAlphaAccessStatus;
  message: string;
  authenticated_issuer: string;
  authenticated_subject: string;
  can_activate: boolean;
  roles: OwnerAlphaRoleProjection[];
}

export interface OwnerAlphaAccessActivationResult {
  access: OwnerAlphaAccessProjection;
  activated: boolean;
}

export class OwnerAlphaAccessError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "OwnerAlphaAccessError";
  }
}

function endpoint(apiBaseUrl: string): string {
  return `${apiBaseUrl.replace(/\/$/, "")}/v1/owner-alpha/operator-access`;
}

async function responseError(response: Response): Promise<OwnerAlphaAccessError> {
  let message = `Operator-access request failed with status ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
  } catch {
    // Preserve the status fallback for non-JSON failures.
  }
  return new OwnerAlphaAccessError(message, response.status);
}

function isProjection(value: unknown): value is OwnerAlphaAccessProjection {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<OwnerAlphaAccessProjection>;
  const statuses: OwnerAlphaAccessStatus[] = [
    "not_configured",
    "identity_not_allowlisted",
    "account_required",
    "athlete_required",
    "revoked",
    "eligible",
    "active",
  ];
  return (
    typeof item.access_version === "string"
    && statuses.includes(item.status as OwnerAlphaAccessStatus)
    && typeof item.message === "string"
    && typeof item.authenticated_issuer === "string"
    && typeof item.authenticated_subject === "string"
    && typeof item.can_activate === "boolean"
    && Array.isArray(item.roles)
    && item.roles.every((role) => (
      role
      && typeof role === "object"
      && ["assessment_reviewer", "planning_reviewer"].includes(role.role)
      && (role.status === null || ["active", "revoked"].includes(role.status))
      && (role.assignment_id === null || typeof role.assignment_id === "string")
    ))
  );
}

export async function fetchOwnerAlphaAccess(
  apiBaseUrl: string,
  fetcher: typeof fetch = fetch,
): Promise<OwnerAlphaAccessProjection> {
  const response = await fetcher(endpoint(apiBaseUrl), {
    headers: authorizedHeaders({ Accept: "application/json" }),
  });
  if (!response.ok) throw await responseError(response);
  const body: unknown = await response.json();
  if (!isProjection(body)) {
    throw new OwnerAlphaAccessError("Operator-access response is invalid.", response.status);
  }
  return body;
}

export async function activateOwnerAlphaAccess(
  apiBaseUrl: string,
  fetcher: typeof fetch = fetch,
): Promise<OwnerAlphaAccessActivationResult> {
  const response = await fetcher(`${endpoint(apiBaseUrl)}/activation`, {
    method: "POST",
    headers: authorizedHeaders({
      Accept: "application/json",
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({ attestation: true }),
  });
  if (!response.ok) throw await responseError(response);
  const body = (await response.json()) as Partial<OwnerAlphaAccessActivationResult>;
  if (!body || typeof body.activated !== "boolean" || !isProjection(body.access)) {
    throw new OwnerAlphaAccessError("Operator-access activation response is invalid.", response.status);
  }
  return body as OwnerAlphaAccessActivationResult;
}
