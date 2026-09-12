import { headers } from "next/headers";

import { isIsoDate, isUuid } from "../lib/current-week";
import { browserAuthMode } from "../lib/identity";
import { readServerSessionAccessToken } from "../lib/server-session";

import { CurrentWeekDashboard } from "./current-week-dashboard";

type HomeProps = {
  searchParams: Promise<{ athleteId?: string | string[]; asOf?: string | string[] }>;
};

export default async function Home({ searchParams }: HomeProps) {
  const { athleteId, asOf } = await searchParams;
  const normalizedAthleteId = typeof athleteId === "string" && isUuid(athleteId.trim())
    ? athleteId.trim()
    : undefined;
  const normalizedAsOf = typeof asOf === "string" && isIsoDate(asOf.trim())
    ? asOf.trim()
    : undefined;
  let authenticated = browserAuthMode !== "session";
  if (!authenticated) {
    try {
      const requestHeaders = await headers();
      authenticated = Boolean(
        await readServerSessionAccessToken(requestHeaders.get("cookie")),
      );
    } catch {
      authenticated = false;
    }
  }
  const returnParams = new URLSearchParams();
  if (normalizedAthleteId) returnParams.set("athleteId", normalizedAthleteId);
  if (normalizedAsOf) returnParams.set("asOf", normalizedAsOf);
  const returnPath = returnParams.size ? `/?${returnParams.toString()}` : "/";
  return (
    <CurrentWeekDashboard
      initialAthleteId={normalizedAthleteId}
      initialAsOf={normalizedAsOf}
      authenticated={authenticated}
      signInHref={`/auth/login?return_to=${encodeURIComponent(returnPath)}`}
    />
  );
}
