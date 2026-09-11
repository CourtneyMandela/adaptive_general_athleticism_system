import { CurrentWeekDashboard } from "./current-week-dashboard";

type HomeProps = {
  searchParams: Promise<{ athleteId?: string | string[]; asOf?: string | string[] }>;
};

export default async function Home({ searchParams }: HomeProps) {
  const { athleteId, asOf } = await searchParams;
  return (
    <CurrentWeekDashboard
      initialAthleteId={typeof athleteId === "string" ? athleteId : undefined}
      initialAsOf={typeof asOf === "string" ? asOf : undefined}
    />
  );
}
