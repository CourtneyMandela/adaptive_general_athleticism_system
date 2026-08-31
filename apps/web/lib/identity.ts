export type BrowserAuthMode = "development" | "session";

const configuredAuthMode = process.env.NEXT_PUBLIC_AGAS_AUTH_MODE?.trim() || "development";

if (configuredAuthMode !== "development" && configuredAuthMode !== "session") {
  throw new Error("NEXT_PUBLIC_AGAS_AUTH_MODE must be development or session.");
}

export const browserAuthMode: BrowserAuthMode = configuredAuthMode;

const configuredDevelopmentToken = process.env.NEXT_PUBLIC_AGAS_DEVELOPMENT_TOKEN?.trim();

export const developmentAccessToken =
  browserAuthMode === "development" ? configuredDevelopmentToken || "dev.local-browser" : "";

const configuredReviewerToken = process.env.NEXT_PUBLIC_AGAS_REVIEWER_TOKEN?.trim();

export const reviewerDevelopmentAccessToken =
  browserAuthMode === "development" ? configuredReviewerToken || developmentAccessToken : "";

const configuredAssessmentReviewerToken =
  process.env.NEXT_PUBLIC_AGAS_ASSESSMENT_REVIEWER_TOKEN?.trim();

export const assessmentReviewerDevelopmentAccessToken =
  browserAuthMode === "development"
    ? configuredAssessmentReviewerToken || "dev.local-assessment-reviewer"
    : "";

export function authorizedHeaders(
  headers: Record<string, string> = {},
  accessToken = developmentAccessToken,
): Record<string, string> {
  if (browserAuthMode === "session") {
    if (Object.keys(headers).some((name) => name.toLowerCase() === "authorization")) {
      throw new Error("Browser code cannot set authorization headers in session mode.");
    }
    return { ...headers };
  }
  if (!accessToken.trim()) {
    throw new Error("A development access token is required.");
  }
  return {
    ...headers,
    Authorization: `Bearer ${accessToken}`,
  };
}
