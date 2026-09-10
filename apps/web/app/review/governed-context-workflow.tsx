"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  createInitialStrategyFromContextReview,
  reviewInitialPlanningContextDraft,
  type InitialPlanningContextDraft,
  type InitialPlanningContextReview,
  type InitialPlanningContextReviewDecision,
  type InitialPlanningPreparationProjection,
  type InitialStrategyCreationResult,
} from "@/lib/initial-planning-review";
import {
  fetchPreparedInitialPlanningContext,
  ratifyPreparedInitialPlanningContext,
  type PreparedInitialPlanningContextCandidate,
  type PreparedInitialPlanningContextProjection,
} from "@/lib/prepared-planning-context";

const reviewRationale =
  "Reviewed the exact system-prepared estimate, floor, policy, adaptation, unused values, provenance, and safety boundary without replacing its content.";
const reviewUncertainty =
  "Approval accepts this narrow owner-alpha planning interpretation only. It does not establish medical clearance, session readiness, exercise feasibility, dose, or guaranteed response.";

function readable(value: string): string {
  return value.replaceAll("_", " ");
}

function CandidateReview({ candidate }: { candidate: PreparedInitialPlanningContextCandidate }) {
  const context = candidate.candidate_context;
  return (
    <>
      <div className="assessment-candidate-meaning">
        <section>
          <h3>Expected planning result</h3>
          <p>
            <strong>{candidate.expected_priority_state.toUpperCase()}</strong>{" "}
            with inspectable score {candidate.expected_priority_score.toFixed(3)}
          </p>
          <p>
            {String(context.capability_estimate_id)} compared with{" "}
            {String(context.competency_floor_id)}.
          </p>
        </section>
        <section>
          <h3>Exact authorities</h3>
          <p>{candidate.policy_version}</p>
          <p>{candidate.floor_version}</p>
          <p>{candidate.estimate_scope}</p>
        </section>
      </div>
      <details open>
        <summary>Why no planning scores were invented</summary>
        <div className="review-candidates">
          {candidate.components.map((component) => (
            <article className="review-candidate" key={component.field}>
              <strong>{readable(component.field)}</strong>
              <span>
                {String(component.value)} · {readable(component.treatment)}
              </span>
              <p>{component.basis}</p>
              <p className="form-help">{component.limitation}</p>
            </article>
          ))}
        </div>
      </details>
      <aside className="review-boundary">
        <strong>Safety boundary</strong>
        <span>{candidate.safety_boundary}</span>
      </aside>
      <details>
        <summary>Rationale, uncertainty, and integrity</summary>
        <p>{candidate.applicability_rationale}</p>
        <p>{candidate.uncertainty}</p>
        <code>{candidate.candidate_version}</code>
        <code>{candidate.content_digest}</code>
      </details>
    </>
  );
}

export function GovernedContextWorkflow({
  apiBaseUrl,
  athleteId,
  projection: preparation,
  onCreated,
}: {
  apiBaseUrl: string;
  athleteId: string;
  projection: InitialPlanningPreparationProjection;
  onCreated: (result: InitialStrategyCreationResult) => void;
}) {
  const [prepared, setPrepared] = useState<PreparedInitialPlanningContextProjection | null>(null);
  const [draft, setDraft] = useState<InitialPlanningContextDraft | null>(null);
  const [review, setReview] = useState<InitialPlanningContextReview | null>(null);
  const [acceptanceConfirmed, setAcceptanceConfirmed] = useState(false);
  const [reviewConfirmed, setReviewConfirmed] = useState(false);
  const [creationConfirmed, setCreationConfirmed] = useState(false);
  const [busy, setBusy] = useState<"loading" | "accept" | "review" | "strategy" | "idle">(
    "loading",
  );
  const [message, setMessage] = useState("");

  const loadPrepared = useCallback(async () => {
    setBusy("loading");
    setMessage("");
    try {
      const loaded = await fetchPreparedInitialPlanningContext(apiBaseUrl, athleteId);
      setPrepared(loaded);
      setDraft(loaded.candidate?.accepted_draft ?? null);
      setReview(loaded.candidate?.accepted_review ?? null);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load the prepared context.");
    } finally {
      setBusy("idle");
    }
  }, [apiBaseUrl, athleteId]);

  useEffect(() => {
    let active = true;
    void fetchPreparedInitialPlanningContext(apiBaseUrl, athleteId)
      .then((loaded) => {
        if (!active) return;
        setPrepared(loaded);
        setDraft(loaded.candidate?.accepted_draft ?? null);
        setReview(loaded.candidate?.accepted_review ?? null);
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(
            error instanceof Error ? error.message : "Unable to load the prepared context.",
          );
        }
      })
      .finally(() => {
        if (active) setBusy("idle");
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl, athleteId]);

  async function acceptCandidate() {
    const candidate = prepared?.candidate;
    if (!candidate || !acceptanceConfirmed) return;
    setBusy("accept");
    setMessage("");
    try {
      const result = await ratifyPreparedInitialPlanningContext(
        apiBaseUrl,
        athleteId,
        candidate,
      );
      setDraft(result.draft);
      setPrepared((current) => current ? {
        ...current,
        status: "accepted",
        candidate: current.candidate ? {
          ...current.candidate,
          status: "accepted",
          accepted_draft_id: result.draft.id,
          accepted_draft: result.draft,
        } : null,
      } : current);
      setAcceptanceConfirmed(false);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to accept the prepared context.");
    } finally {
      setBusy("idle");
    }
  }

  async function submitReview(decision: InitialPlanningContextReviewDecision) {
    if (!draft || !reviewConfirmed) return;
    setBusy("review");
    setMessage("");
    try {
      setReview(await reviewInitialPlanningContextDraft(apiBaseUrl, draft.id, {
        decision,
        reviewed_at: new Date().toISOString(),
        applicability_rationale: reviewRationale,
        uncertainty: reviewUncertainty,
      }));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to record the context review.");
    } finally {
      setBusy("idle");
    }
  }

  async function createStrategy() {
    if (!review || review.decision !== "approved" || !creationConfirmed) return;
    setBusy("strategy");
    setMessage("");
    try {
      onCreated(
        await createInitialStrategyFromContextReview(
          apiBaseUrl,
          review.id,
          new Date().toISOString(),
        ),
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to create the strategy.");
      setBusy("idle");
    }
  }

  if (busy === "loading" && !prepared) {
    return <section className="governed-context"><p>Preparing exact planning context…</p></section>;
  }

  if (!prepared?.candidate) {
    return (
      <section className="governed-context" aria-labelledby="prepared-context-blocked">
        <p className="eyebrow">System preparation</p>
        <h2 id="prepared-context-blocked">One authority still needs review</h2>
        <p>{prepared?.message ?? preparation.message}</p>
        {prepared?.blockers.length ? (
          <ul>{prepared.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}</ul>
        ) : null}
        <div className="context-actions">
          <Link className="primary-button" href="/review/planning-authorities">
            Review prepared authorities
          </Link>
          <button type="button" className="secondary-button" onClick={() => void loadPrepared()}>
            Refresh context
          </button>
        </div>
        {message ? <p className="form-error" role="alert">{message}</p> : null}
      </section>
    );
  }

  const candidate = prepared.candidate;
  return (
    <section className="governed-context" aria-labelledby="prepared-context-title">
      <header>
        <div>
          <p className="eyebrow">
            {draft ? "Step 2 · Immutable review" : "Step 1 · System-prepared context"}
          </p>
          <h2 id="prepared-context-title">
            {draft ? "Review the exact stored draft" : "Review what AGAS prepared"}
          </h2>
          <p>{candidate.summary}</p>
        </div>
        <span className={`status-badge status-badge--${draft ? "ratified" : "available"}`}>
          {draft ? "draft stored" : "ready"}
        </span>
      </header>

      <CandidateReview candidate={candidate} />

      {!draft ? (
        <div className="assessment-candidate-approval">
          <label>
            <input
              type="checkbox"
              checked={acceptanceConfirmed}
              onChange={(event) => setAcceptanceConfirmed(event.target.checked)}
            />
            <span>
              I inspected the exact prepared context and understand that it creates a planning
              draft—not a workout or medical clearance.
            </span>
          </label>
          <button
            type="button"
            className="primary-button"
            disabled={!acceptanceConfirmed || busy !== "idle"}
            onClick={() => void acceptCandidate()}
          >
            {busy === "accept" ? "Storing exact draft…" : "Accept prepared context"}
          </button>
        </div>
      ) : !review ? (
        <div className="context-review-fields">
          <p>
            The immutable draft is stored as <code>{draft.id}</code>. The separate review records
            approval or rejection without changing any value.
          </p>
          <p><strong>Review rationale:</strong> {reviewRationale}</p>
          <p><strong>Review uncertainty:</strong> {reviewUncertainty}</p>
          <label className="context-confirmation">
            <input
              type="checkbox"
              checked={reviewConfirmed}
              onChange={(event) => setReviewConfirmed(event.target.checked)}
            />
            <span>I inspected the persisted candidate, lineage, rationale, and uncertainty.</span>
          </label>
          <div className="context-actions">
            {(["approved", "needs_revision", "rejected"] as const).map((decision) => (
              <button
                key={decision}
                type="button"
                className={decision === "approved" ? "primary-button" : "secondary-button"}
                disabled={!reviewConfirmed || busy !== "idle"}
                onClick={() => void submitReview(decision)}
              >
                {busy === "review" ? "Recording…" : readable(decision)}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="context-review-result">
          <strong>Review decision: {readable(review.decision)}</strong>
          <code>{review.id}</code>
          {review.decision === "approved" ? (
            <>
              <label className="context-confirmation">
                <input
                  type="checkbox"
                  checked={creationConfirmed}
                  onChange={(event) => setCreationConfirmed(event.target.checked)}
                />
                <span>
                  Create the root strategy from this exact approved draft. This still creates no
                  workout.
                </span>
              </label>
              <button
                type="button"
                className="primary-button"
                disabled={!creationConfirmed || busy !== "idle"}
                onClick={() => void createStrategy()}
              >
                {busy === "strategy" ? "Creating strategy…" : "Create initial strategy"}
              </button>
            </>
          ) : (
            <p>This decision remains in history. A changed proposal requires a new prepared draft.</p>
          )}
        </div>
      )}
      {message ? <p className="form-error" role="alert">{message}</p> : null}
    </section>
  );
}
