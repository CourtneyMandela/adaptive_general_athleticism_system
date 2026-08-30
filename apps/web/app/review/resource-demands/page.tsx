import { ResourceDemandReviewClient } from "./resource-demand-review-client";

export default async function ResourceDemandReviewPage({
  searchParams,
}: {
  searchParams: Promise<{ strategyId?: string }>;
}) {
  const { strategyId = "" } = await searchParams;
  return <ResourceDemandReviewClient initialStrategyId={strategyId} />;
}
