import { isUuid } from "./current-week";

export function athleteHomeHref(athleteId: string | undefined, anchor?: string): string {
  const normalizedAthleteId = athleteId?.trim() ?? "";
  const fragment = anchor ? `#${encodeURIComponent(anchor)}` : "";
  if (!isUuid(normalizedAthleteId)) return `/${fragment}`;
  return `/?athleteId=${encodeURIComponent(normalizedAthleteId)}${fragment}`;
}

export function athleteReviewHref(path: string, athleteId: string | undefined): string {
  const normalizedAthleteId = athleteId?.trim() ?? "";
  if (!isUuid(normalizedAthleteId)) return path;
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}athleteId=${encodeURIComponent(normalizedAthleteId)}`;
}
