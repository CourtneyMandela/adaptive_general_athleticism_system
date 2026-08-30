import { PostBlockReviewClient } from "./post-block-review-client";

export default async function PostBlockReviewPage({
  searchParams,
}: {
  searchParams: Promise<{ blockId?: string; blockReviewId?: string }>;
}) {
  const { blockId = "", blockReviewId = "" } = await searchParams;
  return (
    <PostBlockReviewClient
      initialBlockId={blockId}
      initialBlockReviewId={blockReviewId}
    />
  );
}
