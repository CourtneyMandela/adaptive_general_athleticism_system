import { AssessmentGovernanceClient } from "./assessment-governance-client";

export default async function AssessmentGovernancePage({
  searchParams,
}: {
  searchParams: Promise<{ athleteId?: string }>;
}) {
  const { athleteId } = await searchParams;
  return <AssessmentGovernanceClient athleteId={athleteId} />;
}
