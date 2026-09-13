"use client";

import { useCallback, useEffect, useState } from "react";

import {
  fetchCompetencyFloorProposalReviews,
  reviewCompetencyFloorProposal,
  type CompetencyFloorProposalDecision,
  type CompetencyFloorProposalReviewProjection,
} from "@/lib/competency-floor-proposals";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const decisionLabels: Record<CompetencyFloorProposalDecision, string> = {
  advance: "Advance to engineering",
  needs_revision: "Needs changes",
  rejected: "Reject proposal",
};

export function CompetencyFloorProposalClient() {
  const [projection, setProjection] = useState<CompetencyFloorProposalReviewProjection | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [messageKind, setMessageKind] = useState<"error" | "success">("error");

  const refresh = useCallback(async () => {
    setProjection(await fetchCompetencyFloorProposalReviews(apiBaseUrl));
  }, []);

  useEffect(() => {
    let active = true;
    void fetchCompetencyFloorProposalReviews(apiBaseUrl)
      .then((result) => {
        if (active) setProjection(result);
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(error instanceof Error ? error.message : "Unable to load floor proposals.");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function saveReview(proposalId: string, decision: CompetencyFloorProposalDecision) {
    const item = projection?.items.find((value) => value.proposal.proposal_id === proposalId);
    if (!projection || !item) return;
    const typedNote = notes[proposalId]?.trim() ?? "";
    if (decision !== "advance" && !typedNote) {
      setMessageKind("error");
      setMessage("Add a short note explaining what should change or why this proposal should stop.");
      return;
    }
    const rationale = typedNote || (
      "Advance this exact proposal for engineering preparation of its assessment, applicability, "
      + "and governed authority artifacts."
    );
    setSaving(proposalId);
    setMessage("");
    try {
      const result = await reviewCompetencyFloorProposal(
        apiBaseUrl,
        projection.batch,
        item.proposal,
        decision,
        rationale,
      );
      await refresh();
      setMessageKind("success");
      setMessage(
        result.created
          ? `${decisionLabels[decision]} was saved as feedback only. No training rule was activated.`
          : "That exact feedback was already saved. No duplicate record was created.",
      );
    } catch (error) {
      setMessageKind("error");
      setMessage(error instanceof Error ? error.message : "Unable to save proposal feedback.");
    } finally {
      setSaving(null);
    }
  }

  const batch = projection?.batch;
  const sourceById = new Map(batch?.source_catalog.map((source) => [source.source_id, source]));
  const reviewedCount = projection?.items.filter((item) => (
    item.status !== "unreviewed" && item.status !== "stale_review"
  )).length ?? 0;
  const advanceCount = projection?.items.filter((item) => item.status === "advance").length ?? 0;
  const revisionCount = projection?.items.filter((item) => item.status === "needs_revision").length ?? 0;
  const rejectedCount = projection?.items.filter((item) => item.status === "rejected").length ?? 0;

  return (
    <>
      <section className="planning-queue-summary" aria-labelledby="floor-proposal-title">
        <header>
          <div>
            <p className="eyebrow">Research batch · feedback before governance</p>
            <h2 id="floor-proposal-title">Adult competency-floor proposals</h2>
          </div>
          <span className="status-badge status-badge--proposal_only">feedback only</span>
        </header>
        <p>
          Choose what engineering should do next. “Advance” does not approve a floor or create a
          workout; it only asks AGAS engineering to prepare the missing assessment, applicability,
          and governed release.
        </p>
        {batch ? (
          <>
            <dl className="assessment-summary">
              <div><dt>Reviewed</dt><dd>{reviewedCount}/{batch.proposals.length}</dd></div>
              <div><dt>Advance</dt><dd>{advanceCount}</dd></div>
              <div><dt>Needs changes</dt><dd>{revisionCount}</dd></div>
              <div><dt>Rejected</dt><dd>{rejectedCount}</dd></div>
            </dl>
            <p className="form-help">{batch.release_boundary}</p>
            <div className="assessment-candidate-integrity">
              <code>{batch.batch_version}</code>
              <code>{batch.content_digest}</code>
            </div>
          </>
        ) : null}
        {message ? (
          <p className={messageKind === "success" ? "form-success" : "form-error"} role="status">
            {message}
          </p>
        ) : null}
        {!projection && !message ? (
          <p className="planning-queue-empty">Loading researched proposals…</p>
        ) : null}
      </section>

      {projection?.items.map((item) => {
        const proposal = item.proposal;
        const sources = proposal.source_ids.flatMap((sourceId) => {
          const source = sourceById.get(sourceId);
          return source ? [source] : [];
        });
        const direction = proposal.comparison_direction === "higher_is_better"
          ? "higher is better"
          : "lower is better";
        const busy = saving === proposal.proposal_id;
        return (
          <section className="assessment-candidate" key={proposal.proposal_id}>
            <header>
              <div>
                <p className="eyebrow">
                  {proposal.domain.replaceAll("_", " ")} · {proposal.sex_scope.replaceAll("_", " ")}
                </p>
                <h2>{proposal.label}</h2>
              </div>
              <span className={`status-badge status-badge--proposal-${item.status}`}>
                {item.status.replaceAll("_", " ")}
              </span>
            </header>
            <p>{proposal.measurement}</p>
            <div className="assessment-candidate-meaning">
              <section>
                <h3>Proposed threshold</h3>
                <p><strong>{proposal.threshold} {proposal.unit_or_scale}</strong> · {direction}</p>
                <p>Ages {proposal.minimum_age_years}-{proposal.maximum_age_years}</p>
                <p>{proposal.threshold_rationale}</p>
              </section>
              <section>
                <h3>Authority type</h3>
                <p><strong>{proposal.numeric_value_origin.replaceAll("_", " ")}</strong></p>
                <p>{proposal.operational_use_origin.replaceAll("_", " ")}</p>
                <p>{proposal.evidence_gap}</p>
              </section>
            </div>
            <details open>
              <summary>Population applicability</summary>
              <p>{proposal.population_match_notes}</p>
            </details>
            <details>
              <summary>Source table and population</summary>
              {sources.length ? (
                <div className="assessment-candidate-evidence">
                  {sources.map((source) => (
                    <article key={source.source_id}>
                      <h3>{source.table_locator}</h3>
                      <p><strong>Book:</strong> {source.title}, {source.edition} · ISBN {source.isbn13}</p>
                      <p><strong>Location:</strong> {source.page_locator}</p>
                      <p><strong>Population:</strong> {source.source_population}</p>
                      <p><strong>Reported value:</strong> {source.reported_value}</p>
                      <p><strong>Role:</strong> {source.source_role.replaceAll("_", " ")}</p>
                      <ul>{source.limitations.map((value) => <li key={value}>{value}</li>)}</ul>
                    </article>
                  ))}
                </div>
              ) : <p>No numeric evidence source supports this value.</p>}
            </details>
            <details>
              <summary>Must be resolved before release</summary>
              <ul>{proposal.prerequisites_before_release.map((value) => <li key={value}>{value}</li>)}</ul>
            </details>
            <details>
              <summary>Questions considered during review</summary>
              <ul>{proposal.review_questions.map((value) => <li key={value}>{value}</li>)}</ul>
            </details>

            {item.current_review && item.status !== "stale_review" ? (
              <div className="proposal-feedback-history">
                <p><strong>Current feedback:</strong> {decisionLabels[item.current_review.decision]}</p>
                <p>{item.current_review.rationale}</p>
                <p className="form-help">
                  Saved {new Date(item.current_review.reviewed_at).toLocaleString()} · version {item.current_review.sequence_number}
                </p>
              </div>
            ) : null}

            <div className="proposal-feedback-form">
              <label htmlFor={`proposal-note-${proposal.proposal_id}`}>
                Optional note for “Advance”; required for “Needs changes” or “Reject”
              </label>
              <textarea
                id={`proposal-note-${proposal.proposal_id}`}
                value={notes[proposal.proposal_id] ?? ""}
                maxLength={2000}
                rows={3}
                onChange={(event) => setNotes((current) => ({
                  ...current,
                  [proposal.proposal_id]: event.target.value,
                }))}
                placeholder="Tell engineering what seems wrong, impractical, or worth preserving."
              />
              <div className="proposal-feedback-actions">
                {(["advance", "needs_revision", "rejected"] as const).map((decision) => (
                  <button
                    type="button"
                    className={decision === "advance" ? "primary-button" : "secondary-button"}
                    disabled={saving !== null}
                    key={decision}
                    onClick={() => void saveReview(proposal.proposal_id, decision)}
                  >
                    {busy ? "Saving…" : decisionLabels[decision]}
                  </button>
                ))}
              </div>
              <p className="form-help">
                Saving feedback creates no floor, assessment, training plan, or workout.
              </p>
            </div>
            <div className="assessment-candidate-integrity">
              <code>{proposal.proposal_version}</code>
              <code>{proposal.content_digest}</code>
            </div>
          </section>
        );
      })}
    </>
  );
}
