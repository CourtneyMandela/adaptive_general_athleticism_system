import { describe, expect, it, vi } from "vitest";

import {
  AssessmentGovernanceError,
  fetchAssessmentGovernance,
  fetchAssessmentGovernanceCandidates,
  ratifyAssessmentGovernanceCandidate,
  type AssessmentGovernanceCandidate,
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

  it("loads prepared candidates and ratifies only their exact digest", async () => {
    const candidate: AssessmentGovernanceCandidate = {
      candidate_version: "assessment-governance-candidate@1.0.0",
      candidate_id: "94000000-0000-4000-8000-000000000001",
      slug: "thirty_second_chair_stand",
      release_label: "30-second chair stand owner-alpha release",
      prepared_at: "2026-09-08T10:45:00Z",
      content_digest: `sha256:${"a".repeat(64)}`,
      summary: "A narrow assessment candidate.",
      measures: "Assessment-specific performance.",
      does_not_measure: ["A universal score."],
      capability_domain: "muscular_endurance",
      estimate_scope: "assessment_specific:thirty_second_chair_stand_repetitions",
      setup_requirements: ["A stable chair."],
      protocol_steps: ["Follow the exact protocol."],
      stop_conditions: ["Stop for concerning symptoms."],
      operational_choices: ["One recorded trial."],
      unresolved_limitations: ["Population transfer is uncertain."],
      evidence: [{
        title: "Primary study",
        source_url: "https://pubmed.ncbi.nlm.nih.gov/35949374/",
        population: "Study population.",
        finding: "Narrow finding.",
        limitations: ["Single study."],
        conflict_disclosure: "No declared conflicts.",
      }],
    };
    const fetcher = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(JSON.stringify({
        projected_at: "2026-09-08T15:00:00Z",
        projection_version: "assessment-governance-candidates@1.0.0",
        items: [{ candidate, status: "available", ratified_at: null, issues: [] }],
      }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 201 }));

    await expect(fetchAssessmentGovernanceCandidates("http://localhost:8000/", fetcher))
      .resolves.toMatchObject({ items: [{ candidate }] });
    await expect(ratifyAssessmentGovernanceCandidate("http://localhost:8000/", candidate, fetcher))
      .resolves.toEqual({ ok: true });

    expect(fetcher.mock.calls[1]).toEqual([
      `http://localhost:8000/v1/operator/assessment-governance/candidates/${candidate.candidate_id}/ratifications`,
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          Authorization: "Bearer dev.local-assessment-reviewer",
        },
        body: JSON.stringify({
          candidate_version: candidate.candidate_version,
          content_digest: candidate.content_digest,
          approval_attestation: true,
        }),
      },
    ]);
  });
});
