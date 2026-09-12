import { describe, expect, it, vi } from "vitest";

import {
  AthleteDirectoryRequestError,
  fetchOwnedAthleteDirectory,
} from "./athlete-directory";

const firstId = "00000000-0000-4000-8000-000000000001";
const secondId = "00000000-0000-4000-8000-000000000002";

function directory() {
  return {
    projection_version: "account-athlete-directory@1.0.0",
    athletes: [
      {
        athlete_id: firstId,
        display_name: "Courtney Szabo",
        profile_created_at: "2026-09-12T10:00:00Z",
        goals: ["Build broad athletic capacity"],
        environments: [{ environment_id: secondId, name: "Home" }],
        ownership_granted_at: "2026-09-12T10:00:00Z",
        ownership_rule_version: "profile-environment-onboarding@1.0.0",
      },
    ],
  };
}

describe("owned athlete directory client", () => {
  it("loads only the server-owned profile directory with authorization", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(Response.json(directory()));

    await expect(fetchOwnedAthleteDirectory("http://localhost:8000/", fetcher)).resolves.toEqual(
      directory(),
    );
    expect(fetcher).toHaveBeenCalledWith("http://localhost:8000/v1/athletes", {
      headers: {
        Accept: "application/json",
        Authorization: "Bearer dev.local-browser",
      },
      cache: "no-store",
    });
  });

  it("rejects malformed or unversioned directory responses", async () => {
    const malformed = vi
      .fn<typeof fetch>()
      .mockResolvedValue(Response.json({ ...directory(), projection_version: "future" }));
    await expect(fetchOwnedAthleteDirectory("http://localhost:8000", malformed)).rejects.toEqual(
      new AthleteDirectoryRequestError("The athlete profile directory is invalid.", 502),
    );
  });

  it("preserves a safe server failure detail", async () => {
    const unavailable = vi
      .fn<typeof fetch>()
      .mockResolvedValue(Response.json({ detail: "Authentication is required." }, { status: 401 }));
    await expect(fetchOwnedAthleteDirectory("/api/agas", unavailable)).rejects.toEqual(
      new AthleteDirectoryRequestError("Authentication is required.", 401),
    );
  });
});
