import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/headers", () => ({
  headers: vi.fn(async () => new Headers()),
}));

vi.mock("./current-week-dashboard", () => ({
  CurrentWeekDashboard: () => null,
}));

type DashboardProps = {
  authenticated: boolean;
  initialAthleteId?: string;
  initialAsOf?: string;
  signInHref: string;
};

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("hosted home session boundary", () => {
  it("renders a signed-out dashboard state without treating it as profile-recovery failure", async () => {
    vi.stubEnv("NEXT_PUBLIC_AGAS_AUTH_MODE", "session");
    vi.stubEnv(
      "AGAS_SESSION_ENCRYPTION_KEY",
      "KSkpKSkpKSkpKSkpKSkpKSkpKSkpKSkpKSkpKSkpKSk",
    );
    const { default: Home } = await import("./page");

    const element = await Home({ searchParams: Promise.resolve({}) }) as ReactElement<DashboardProps>;

    expect(element.props.authenticated).toBe(false);
    expect(element.props.signInHref).toBe("/auth/login?return_to=%2F");
  });

  it("preserves only valid athlete and date context through sign-in", async () => {
    vi.stubEnv("NEXT_PUBLIC_AGAS_AUTH_MODE", "session");
    vi.stubEnv(
      "AGAS_SESSION_ENCRYPTION_KEY",
      "KSkpKSkpKSkpKSkpKSkpKSkpKSkpKSkpKSkpKSkpKSk",
    );
    const { default: Home } = await import("./page");
    const athleteId = "d0000000-0000-4000-8000-000000000001";

    const element = await Home({
      searchParams: Promise.resolve({ athleteId, asOf: "2026-09-12" }),
    }) as ReactElement<DashboardProps>;

    expect(element.props.initialAthleteId).toBe(athleteId);
    expect(element.props.initialAsOf).toBe("2026-09-12");
    expect(element.props.signInHref).toBe(
      `/auth/login?return_to=${encodeURIComponent(`/?athleteId=${athleteId}&asOf=2026-09-12`)}`,
    );
  });
});
