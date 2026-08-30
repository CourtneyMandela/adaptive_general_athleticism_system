import { BlockReviewClient } from "./block-review-client";

export default async function BlockReviewPage({
  searchParams,
}: {
  searchParams: Promise<{ strategyId?: string }>;
}) {
  const { strategyId = "" } = await searchParams;
  return <BlockReviewClient initialStrategyId={strategyId} />;
}
