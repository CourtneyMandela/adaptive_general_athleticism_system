const configuredDevelopmentToken = process.env.NEXT_PUBLIC_AGAS_DEVELOPMENT_TOKEN?.trim();

export const developmentAccessToken = configuredDevelopmentToken || "dev.local-browser";

const configuredReviewerToken = process.env.NEXT_PUBLIC_AGAS_REVIEWER_TOKEN?.trim();

export const reviewerDevelopmentAccessToken =
  configuredReviewerToken || developmentAccessToken;

const configuredAssessmentReviewerToken =
  process.env.NEXT_PUBLIC_AGAS_ASSESSMENT_REVIEWER_TOKEN?.trim();

export const assessmentReviewerDevelopmentAccessToken =
  configuredAssessmentReviewerToken || "dev.local-assessment-reviewer";

export function authorizedHeaders(
  headers: Record<string, string> = {},
  accessToken = developmentAccessToken,
): Record<string, string> {
  if (!accessToken.trim()) {
    throw new Error("A development access token is required.");
  }
  return {
    ...headers,
    Authorization: `Bearer ${accessToken}`,
  };
}
