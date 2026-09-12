import { PlanningGovernanceClient } from "./planning-governance-client";

export default async function PlanningGovernancePage({
  searchParams,
}: {
  searchParams: Promise<{ athleteId?: string }>;
}) {
  const { athleteId } = await searchParams;
  return <PlanningGovernanceClient athleteId={athleteId} />;
}
