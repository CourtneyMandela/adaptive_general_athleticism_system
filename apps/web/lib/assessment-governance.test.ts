import { describe, expect, it, vi } from "vitest";

import {
  AssessmentGovernanceError,
  fetchAssessmentGovernance,
} from "./assessment-governance";

describe("assessment-governance client", () => {
  it("uses the dedicated assessment-reviewer token", async () => {
    const projection = {
      projected_at: "2026-08-30T16:00:00Z",
      projection_version: "assessment-governance-workbench@1.1.0",
      items: [],
    };
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(projection), { status: 200 }),
    );

    await expect(fetchAssessmentGovernance("http://localhost:8000/", fetcher)).resolves.toEqual(
      projection,
    );
    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/v1/operator/assessment-governance",
      {
        headers: {
          Accept: "application/json",
          Authorization: "Bearer dev.local-assessment-reviewer",
        },
      },
    );
  });

  it("rejects malformed projection contracts", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ items: [{ definition: {} }] }), { status: 200 }),
    );

    await expect(fetchAssessmentGovernance("http://localhost:8000", fetcher)).rejects.toEqual(
      new AssessmentGovernanceError("Assessment-governance response is invalid.", 200),
    );
  });
});
