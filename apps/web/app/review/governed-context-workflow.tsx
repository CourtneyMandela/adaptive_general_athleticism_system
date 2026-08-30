"use client";

import { FormEvent, useState } from "react";

import {
  createInitialPlanningContextDraft,
  createInitialStrategyFromContextReview,
  reviewInitialPlanningContextDraft,
  type InitialPlanningCandidateContext,
  type InitialPlanningContextDraft,
  type InitialPlanningContextReview,
  type InitialPlanningContextReviewDecision,
  type InitialPlanningPreparationProjection,
  type InitialStrategyCreationResult,
} from "@/lib/initial-planning-review";

const scoreFields = [
  ["general_relevance", "General relevance"],
  ["goal_relevance", "Goal relevance"],
  ["prerequisite_value", "Prerequisite value"],
  ["expected_trainability", "Expected trainability"],
  ["transfer_value", "General transfer"],
  ["fatigue_cost", "Fatigue cost"],
  ["time_cost", "Time cost"],
  ["interference_cost", "Interference cost"],
] as const;

type ScoreField = (typeof scoreFields)[number][0];
type ScoreInputs = Record<ScoreField, string>;

interface CandidateEditorState {
  key: number;
  estimateId: string;
  floorId: string;
  adaptationId: string;
  scores: ScoreInputs;
  safeToTrain: boolean;
  introductoryExposureNeeded: boolean;
  prerequisitesMet: boolean;
  cultivateComparativeAdvantage: boolean;
}

function emptyScores(): ScoreInputs {
  return Object.fromEntries(scoreFields.map(([field]) => [field, ""])) as ScoreInputs;
}

function newCandidate(
  projection: InitialPlanningPreparationProjection,
  key: number,
): CandidateEditorState | null {
  const option = projection.estimate_options.find(
    (item) => item.floor_options.length > 0 && item.adaptation_options.length > 0,
  );
  if (!option) return null;
  return {
    key,
    estimateId: "",
    floorId: "",
    adaptationId: "",
    scores: emptyScores(),
    safeToTrain: false,
    introductoryExposureNeeded: false,
    prerequisitesMet: false,
    cultivateComparativeAdvantage: false,
  };
}

function parseScore(value: string, label: string): number {
  const score = Number(value);
  if (!value.trim() || !Number.isFinite(score) || score < 0 || score > 1) {
    throw new Error(`${label} must be explicitly entered from 0 to 1.`);
  }
  return score;
}

export function GovernedContextWorkflow({
  apiBaseUrl,
  athleteId,
  projection,
  onCreated,
}: {
  apiBaseUrl: string;
  athleteId: string;
  projection: InitialPlanningPreparationProjection;
  onCreated: (result: InitialStrategyCreationResult) => void;
}) {
  const initialCandidate = newCandidate(projection, 1);
  const [candidates, setCandidates] = useState<CandidateEditorState[]>(
    initialCandidate ? [initialCandidate] : [],
  );
  const [nextKey, setNextKey] = useState(2);
  const [policyId, setPolicyId] = useState("");
  const [horizonMonths, setHorizonMonths] = useState("12");
  const [reviewAfterDays, setReviewAfterDays] = useState("42");
  const [draftRationale, setDraftRationale] = useState("");
  const [draftUncertainty, setDraftUncertainty] = useState("");
  const [draft, setDraft] = useState<InitialPlanningContextDraft | null>(null);
  const [reviewRationale, setReviewRationale] = useState("");
  const [reviewUncertainty, setReviewUncertainty] = useState("");
  const [reviewConfirmed, setReviewConfirmed] = useState(false);
  const [review, setReview] = useState<InitialPlanningContextReview | null>(null);
  const [creationConfirmed, setCreationConfirmed] = useState(false);
  const [busy, setBusy] = useState<"idle" | "draft" | "review" | "strategy">("idle");
  const [message, setMessage] = useState("");

  const policyOption = projection.priority_policy_options.find(
    (item) => item.policy.id === policyId,
  );

  function updateCandidate(key: number, update: Partial<CandidateEditorState>) {
    setCandidates((current) =>
      current.map((candidate) =>
        candidate.key === key ? { ...candidate, ...update } : candidate,
      ),
    );
  }

  function changeEstimate(candidate: CandidateEditorState, estimateId: string) {
    const option = projection.estimate_options.find(
      (item) => item.estimate.id === estimateId,
    );
    if (!option) return;
    updateCandidate(candidate.key, {
      estimateId,
      floorId: "",
      adaptationId: "",
    });
  }

  function addCandidate() {
    const candidate = newCandidate(projection, nextKey);
    if (!candidate) return;
    setCandidates((current) => [...current, candidate]);
    setNextKey((current) => current + 1);
  }

  function materializeCandidates(): InitialPlanningCandidateContext[] {
    const adaptationIds = candidates.map((item) => item.adaptationId);
    if (new Set(adaptationIds).size !== adaptationIds.length) {
      throw new Error("Each adaptation may appear in the draft only once.");
    }
    return candidates.map((candidate, index) => {
      const option = projection.estimate_options.find(
        (item) => item.estimate.id === candidate.estimateId,
      );
      const floor = option?.floor_options.find(
        (item) => item.floor.id === candidate.floorId,
      );
      const adaptation = option?.adaptation_options.find(
        (item) => item.id === candidate.adaptationId,
      );
      if (!option || !floor || !adaptation) {
        throw new Error(`Candidate ${index + 1} must use one eligible estimate pathway.`);
      }
      return {
        adaptation_id: adaptation.id,
        competency_floor_id: floor.floor.id,
        competency_floor_review_id: floor.review.id,
        capability_estimate_id: option.estimate.id,
        general_relevance: parseScore(candidate.scores.general_relevance, "General relevance"),
        goal_relevance: parseScore(candidate.scores.goal_relevance, "Goal relevance"),
        prerequisite_value: parseScore(candidate.scores.prerequisite_value, "Prerequisite value"),
        expected_trainability: parseScore(
          candidate.scores.expected_trainability,
          "Expected trainability",
        ),
        transfer_value: parseScore(candidate.scores.transfer_value, "General transfer"),
        fatigue_cost: parseScore(candidate.scores.fatigue_cost, "Fatigue cost"),
        time_cost: parseScore(candidate.scores.time_cost, "Time cost"),
        interference_cost: parseScore(candidate.scores.interference_cost, "Interference cost"),
        safe_to_train: candidate.safeToTrain,
        introductory_exposure_needed: candidate.introductoryExposureNeeded,
        prerequisites_met: candidate.prerequisitesMet,
        prerequisite_adaptation_ids: [],
        cultivate_comparative_advantage: candidate.cultivateComparativeAdvantage,
        source_observation_ids: option.estimate.source_observation_ids,
        evidence_claim_ids: [],
      };
    });
  }

  async function saveDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    if (!policyOption || candidates.length === 0) {
      setMessage("An approved policy and at least one eligible candidate are required.");
      return;
    }
    setBusy("draft");
    try {
      const created = await createInitialPlanningContextDraft(apiBaseUrl, athleteId, {
        priority_policy_id: policyOption.policy.id,
        priority_policy_review_id: policyOption.review.id,
        candidate_contexts: materializeCandidates(),
        horizon_months: Number(horizonMonths),
        review_after_days: Number(reviewAfterDays),
        authored_at: new Date().toISOString(),
        applicability_rationale: draftRationale,
        uncertainty: draftUncertainty,
      });
      setDraft(created);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save the context draft.");
    } finally {
      setBusy("idle");
    }
  }

  async function submitReview(decision: InitialPlanningContextReviewDecision) {
    if (!draft || !reviewConfirmed) return;
    setBusy("review");
    setMessage("");
    try {
      setReview(
        await reviewInitialPlanningContextDraft(apiBaseUrl, draft.id, {
          decision,
          reviewed_at: new Date().toISOString(),
          applicability_rationale: reviewRationale,
          uncertainty: reviewUncertainty,
        }),
      );
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

  if (draft) {
    return (
      <section className="governed-context" aria-labelledby="governed-review-title">
        <p className="eyebrow">Step 2 · Immutable review</p>
        <h2 id="governed-review-title">Review the exact persisted draft</h2>
        <p>
          Draft <code>{draft.id}</code> contains {draft.candidate_contexts.length} explicit
          candidate judgment(s). Editing now requires a new draft.
        </p>
        <div className="review-candidates">
          {draft.candidate_contexts.map((candidate, index) => (
            <article className="review-candidate" key={candidate.adaptation_id}>
              <strong>Candidate {index + 1} · {candidate.adaptation_id}</strong>
              <span>{candidate.capability_estimate_id}</span>
              <dl className="review-scores">
                {scoreFields.map(([field, label]) => (
                  <div key={field}><dt>{label}</dt><dd>{candidate[field].toFixed(2)}</dd></div>
                ))}
              </dl>
            </article>
          ))}
        </div>
        {!review ? (
          <div className="context-review-fields">
            <label>
              Review rationale
              <textarea
                value={reviewRationale}
                onChange={(event) => setReviewRationale(event.target.value)}
                rows={3}
              />
            </label>
            <label>
              Review uncertainty
              <textarea
                value={reviewUncertainty}
                onChange={(event) => setReviewUncertainty(event.target.value)}
                rows={3}
              />
            </label>
            <label className="context-confirmation">
              <input
                type="checkbox"
                checked={reviewConfirmed}
                onChange={(event) => setReviewConfirmed(event.target.checked)}
              />
              <span>I inspected the persisted candidate values, lineage, rationale, and uncertainty.</span>
            </label>
            <div className="context-actions">
              {(["approved", "needs_revision", "rejected"] as const).map((decision) => (
                <button
                  key={decision}
                  type="button"
                  className={decision === "approved" ? "primary-button" : "secondary-button"}
                  disabled={
                    !reviewConfirmed || !reviewRationale.trim() ||
                    !reviewUncertainty.trim() || busy !== "idle"
                  }
                  onClick={() => void submitReview(decision)}
                >
                  {decision.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="context-review-result">
            <strong>Decision: {review.decision.replace("_", " ")}</strong>
            <code>{review.id}</code>
            {review.decision === "approved" ? (
              <>
                <label className="context-confirmation">
                  <input
                    type="checkbox"
                    checked={creationConfirmed}
                    onChange={(event) => setCreationConfirmed(event.target.checked)}
                  />
                  <span>Create the root strategy from this exact approved artifact.</span>
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
              <p>A replacement requires a new draft; this decision remains in history.</p>
            )}
          </div>
        )}
        {message ? <p className="form-error" role="alert">{message}</p> : null}
      </section>
    );
  }

  return (
    <form className="governed-context" onSubmit={saveDraft}>
      <header>
        <div>
          <p className="eyebrow">Step 1 · Governed authoring</p>
          <h2>Author explicit candidate judgments</h2>
          <p>
            Values are intentionally blank. They are reviewer judgments—not measurements—and are
            never inferred from the displayed estimate.
          </p>
        </div>
      </header>
      <div className="context-plan-fields">
        <label>
          Approved priority policy
          <select value={policyId} onChange={(event) => setPolicyId(event.target.value)}>
            <option value="" disabled>Select an exact approved policy</option>
            {projection.priority_policy_options.map(({ policy }) => (
              <option key={policy.id} value={policy.id}>{policy.policy_version}</option>
            ))}
          </select>
        </label>
        <label>
          Horizon months
          <input type="number" min="6" max="24" value={horizonMonths} onChange={(event) => setHorizonMonths(event.target.value)} required />
        </label>
        <label>
          Review after days
          <input type="number" min="1" value={reviewAfterDays} onChange={(event) => setReviewAfterDays(event.target.value)} required />
        </label>
      </div>
      <div className="context-candidates">
        {candidates.map((candidate, index) => {
          const option = projection.estimate_options.find(
            (item) => item.estimate.id === candidate.estimateId,
          );
          return (
            <fieldset className="context-candidate-editor" key={candidate.key}>
              <legend>Candidate {index + 1}</legend>
              <div className="context-selects">
                <label>
                  Capability estimate
                  <select value={candidate.estimateId} onChange={(event) => changeEstimate(candidate, event.target.value)}>
                    <option value="" disabled>Select an eligible estimate</option>
                    {projection.estimate_options.map((item) => (
                      <option key={item.estimate.id} value={item.estimate.id}>
                        {item.estimate.domain.replaceAll("_", " ")} · {String(item.estimate.estimate)} {item.estimate.unit_or_scale}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Approved competency floor
                  <select value={candidate.floorId} onChange={(event) => updateCandidate(candidate.key, { floorId: event.target.value })}>
                    <option value="" disabled>Select an approved floor</option>
                    {option?.floor_options.map(({ floor }) => (
                      <option key={floor.id} value={floor.id}>{floor.threshold} {floor.unit_or_scale} · {floor.floor_version}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Adaptation
                  <select value={candidate.adaptationId} onChange={(event) => updateCandidate(candidate.key, { adaptationId: event.target.value })}>
                    <option value="" disabled>Select an adaptation</option>
                    {option?.adaptation_options.map((adaptation) => (
                      <option key={adaptation.id} value={adaptation.id}>{adaptation.name}</option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="context-score-grid">
                {scoreFields.map(([field, label]) => (
                  <label key={field}>
                    {label}
                    <input
                      type="number"
                      min="0"
                      max="1"
                      step="0.05"
                      value={candidate.scores[field]}
                      onChange={(event) => updateCandidate(candidate.key, { scores: { ...candidate.scores, [field]: event.target.value } })}
                      required
                    />
                  </label>
                ))}
              </div>
              <div className="context-flags">
                {[
                  ["safeToTrain", "Explicitly cleared as safe to train"],
                  ["prerequisitesMet", "Prerequisites reviewed as met"],
                  ["introductoryExposureNeeded", "Introductory exposure needed"],
                  ["cultivateComparativeAdvantage", "Cultivate comparative advantage"],
                ].map(([field, label]) => (
                  <label key={field}>
                    <input
                      type="checkbox"
                      checked={candidate[field as keyof Pick<CandidateEditorState, "safeToTrain" | "prerequisitesMet" | "introductoryExposureNeeded" | "cultivateComparativeAdvantage">]}
                      onChange={(event) => updateCandidate(candidate.key, { [field]: event.target.checked })}
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
              {candidates.length > 1 ? (
                <button type="button" className="text-button" onClick={() => setCandidates((current) => current.filter((item) => item.key !== candidate.key))}>Remove candidate</button>
              ) : null}
            </fieldset>
          );
        })}
      </div>
      <button type="button" className="secondary-button" onClick={addCandidate}>Add candidate</button>
      <div className="context-review-fields">
        <label>
          Draft applicability rationale
          <textarea value={draftRationale} onChange={(event) => setDraftRationale(event.target.value)} rows={3} required />
        </label>
        <label>
          Draft uncertainty
          <textarea value={draftUncertainty} onChange={(event) => setDraftUncertainty(event.target.value)} rows={3} required />
        </label>
      </div>
      <button type="submit" className="primary-button" disabled={busy !== "idle"}>
        {busy === "draft" ? "Saving immutable draft…" : "Save context draft"}
      </button>
      {message ? <p className="form-error" role="alert">{message}</p> : null}
    </form>
  );
}
