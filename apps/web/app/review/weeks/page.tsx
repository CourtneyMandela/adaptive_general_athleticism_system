import { FirstWeekReviewClient } from "./first-week-review-client";

export default async function FirstWeekReviewPage({
  searchParams,
}: {
  searchParams: Promise<{ blockId?: string }>;
}) {
  const { blockId = "" } = await searchParams;
  return <FirstWeekReviewClient initialBlockId={blockId} />;
}
