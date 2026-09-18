import { PlanningReviewQueueClient } from "./planning-review-queue-client";
import { isUuid } from "@/lib/current-week";

type PlanningReviewQueuePageProps = {
  searchParams: Promise<{ athleteId?: string | string[] }>;
};

export default async function PlanningReviewQueuePage({ searchParams }: PlanningReviewQueuePageProps) {
  const { athleteId } = await searchParams;
  const normalizedAthleteId = typeof athleteId === "string" && isUuid(athleteId.trim())
    ? athleteId.trim()
    : undefined;
  return (
    <PlanningReviewQueueClient
      athleteId={normalizedAthleteId}
    />
  );
}
