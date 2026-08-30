import { CurrentWeekDashboard } from "./current-week-dashboard";

type HomeProps = {
  searchParams: Promise<{ athleteId?: string | string[] }>;
};

export default async function Home({ searchParams }: HomeProps) {
  const athleteId = (await searchParams).athleteId;
  return (
    <CurrentWeekDashboard
      initialAthleteId={typeof athleteId === "string" ? athleteId : undefined}
    />
  );
}
