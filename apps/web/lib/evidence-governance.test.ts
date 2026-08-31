import { describe, expect, it, vi } from "vitest";

import { EvidenceGovernanceError, fetchEvidenceGovernance } from "./evidence-governance";

describe("evidence-governance client", () => {
  it("uses the scientific-governance inspection token", async () => {
    const projection = {
      projected_at: "2026-08-31T16:00:00Z",
      projection_version: "evidence-governance-workbench@1.0.0",
      items: [],
    };
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(projection), { status: 200 }),
    );

    await expect(fetchEvidenceGovernance("http://localhost:8000/", fetcher)).resolves.toEqual(
      projection,
    );
    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/v1/operator/evidence-governance",
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
      new Response(JSON.stringify({ items: [{ claim: {} }] }), { status: 200 }),
    );

    await expect(fetchEvidenceGovernance("http://localhost:8000", fetcher)).rejects.toEqual(
      new EvidenceGovernanceError("Evidence-governance response is invalid.", 200),
    );
  });
});
