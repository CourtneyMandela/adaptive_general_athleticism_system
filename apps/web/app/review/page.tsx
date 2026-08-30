"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";

import { GovernedContextWorkflow } from "./governed-context-workflow";

import {
  fetchInitialPlanningPreparation,
  isUuid,
  parseInitialStrategyDraft,
  submitInitialStrategy,
  type InitialStrategyCreationResult,
  type InitialPlanningPreparationProjection,
  type OperatorInitialStrategyRequest,
} from "@/lib/initial-planning-review";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const scoreLabels: Array<
  [
    keyof Pick<
      OperatorInitialStrategyRequest["candidate_contexts"][number],
      | "general_relevance"
      | "goal_relevance"
      | "prerequisite_value"
      | "expected_trainability"
      | "transfer_value"
      | "fatigue_cost"
      | "time_cost"
      | "interference_cost"
    >,
    string,
  ]
> = [
  ["general_relevance", "General relevance"],
  ["goal_relevance", "Goal relevance"],
  ["prerequisite_value", "Prerequisite value"],
  ["expected_trainability", "Expected trainability"],
  ["transfer_value", "Transfer value"],
  ["fatigue_cost", "Fatigue cost"],
  ["time_cost", "Time cost"],
  ["interference_cost", "Interference cost"],
];

const preparationStatusLabels: Record<
  InitialPlanningPreparationProjection["status"],
  string
> = {
  capability_estimate_required: "Estimate required",
  capability_estimate_stale: "Reassessment required",
  planning_authorities_required: "Authorities required",
  planning_context_review_required: "Ready for context review",
  initial_strategy_exists: "Strategy already exists",
};

function formatUnknownValue(value: unknown): string {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function PreparationContext({
  projection,
}: {
  projection: InitialPlanningPreparationProjection;
}) {
  return (
    <section className="review-preparation" aria-labelledby="review-preparation-title">
      <header>
        <div>
          <p className="eyebrow">Authoritative preparation</p>
          <h2 id="review-preparation-title">{projection.athlete_display_name}</h2>
          <p>{projection.message}</p>
        </div>
        <span className={`status-badge status-badge--${projection.status}`}>
          {preparationStatusLabels[projection.status]}
        </span>
      </header>
      <dl className="review-metadata">
        <div>
          <dt>Current estimates</dt>
          <dd>{projection.estimate_options.length}</dd>
        </div>
        <div>
          <dt>Stale estimates</dt>
          <dd>{projection.stale_estimates.length}</dd>
        </div>
        <div>
          <dt>Approved policies</dt>
          <dd>{projection.priority_policy_options.length}</dd>
        </div>
        <div>
          <dt>Referenced evidence</dt>
          <dd>{projection.evidence_claims.length}</dd>
        </div>
      </dl>

      {projection.initial_strategy_id ? (
        <p className="review-existing-strategy">
          Existing root strategy: <code>{projection.initial_strategy_id}</code>
        </p>
      ) : null}

      <section className="preparation-group" aria-labelledby="policy-options-title">
        <h3 id="policy-options-title">Approved priority policies</h3>
        {projection.priority_policy_options.length ? (
          <div className="preparation-options">
            {projection.priority_policy_options.map(({ policy, review }) => (
              <article key={policy.id} className="preparation-option">
                <strong>{policy.policy_version}</strong>
                <code>{policy.id}</code>
                <p>Exact review <code>{review.id}</code></p>
                <p>
                  Reviewed {new Date(review.reviewed_at).toLocaleString()} · {review.review_version}
                </p>
                <details>
                  <summary>Scoring policy and review rationale</summary>
                  <dl className="policy-values">
                    <div><dt>Deficit weight</dt><dd>{policy.deficit_weight}</dd></div>
                    <div><dt>General relevance</dt><dd>{policy.general_relevance_weight}</dd></div>
                    <div><dt>Goal relevance</dt><dd>{policy.goal_relevance_weight}</dd></div>
                    <div><dt>Develop threshold</dt><dd>{policy.develop_score_threshold}</dd></div>
                    <div><dt>Max DEVELOP</dt><dd>{policy.max_develop_adaptations}</dd></div>
                    <div><dt>Cost penalty</dt><dd>{policy.cost_penalty}</dd></div>
                  </dl>
                  <p>{review.applicability_rationale}</p>
                  <p><strong>Uncertainty:</strong> {review.uncertainty}</p>
                </details>
              </article>
            ))}
          </div>
        ) : <p className="form-help">No current approved priority policy is available.</p>}
      </section>

      <section className="preparation-group" aria-labelledby="estimate-options-title">
        <h3 id="estimate-options-title">Current estimate pathways</h3>
        {projection.estimate_options.length ? (
          <div className="preparation-options">
            {projection.estimate_options.map((option) => (
              <article key={option.estimate.id} className="preparation-option estimate-option">
                <header>
                  <div>
                    <strong>{option.estimate.domain.replaceAll("_", " ")}</strong>
                    <p>{option.estimate.estimate_scope}</p>
                  </div>
                  <span className="status-badge">{option.estimate.confidence}</span>
                </header>
                <p className="estimate-reading">
                  {formatUnknownValue(option.estimate.estimate)} {option.estimate.unit_or_scale}
                </p>
                <code>{option.estimate.id}</code>
                <p className="form-help">
                  {option.estimate.calculation_method} · {option.estimate.rule_version}
                </p>
                <details>
                  <summary>{option.source_observations.length} source observation(s)</summary>
                  <ul className="preparation-detail-list">
                    {option.source_observations.map((observation) => (
                      <li key={observation.id}>
                        <strong>{observation.observation_type}</strong>
                        <span>
                          {formatUnknownValue(observation.measurement)} {observation.unit ?? ""} ·{" "}
                          {observation.reliability} reliability
                        </span>
                        <code>{observation.id}</code>
                      </li>
                    ))}
                  </ul>
                </details>
                <details open>
                  <summary>{option.floor_options.length} compatible approved floor(s)</summary>
                  <ul className="preparation-detail-list">
                    {option.floor_options.map(({ floor, review }) => (
                      <li key={floor.id}>
                        <strong>
                          {floor.comparison_direction.replaceAll("_", " ")} {floor.threshold}{" "}
                          {floor.unit_or_scale}
                        </strong>
                        <span>{floor.population} · {floor.floor_version}</span>
                        <code>{floor.id}</code>
                        <span>Exact review</span>
                        <code>{review.id}</code>
                        <span>{floor.applicability_notes}</span>
                      </li>
                    ))}
                  </ul>
                </details>
                <details open>
                  <summary>{option.adaptation_options.length} domain-compatible adaptation(s)</summary>
                  <ul className="preparation-detail-list">
                    {option.adaptation_options.map((adaptation) => (
                      <li key={adaptation.id}>
                        <strong>{adaptation.name}</strong>
                        <code>{adaptation.id}</code>
                        <span>
                          {adaptation.preferred_stimuli.length
                            ? adaptation.preferred_stimuli.join(", ").replaceAll("_", " ")
                            : "No preferred stimulus metadata"}
                        </span>
                      </li>
                    ))}
                  </ul>
                </details>
              </article>
            ))}
          </div>
        ) : <p className="form-help">No current estimate is eligible for context review.</p>}
      </section>

      <details className="preparation-evidence">
        <summary>{projection.evidence_claims.length} referenced evidence claim(s)</summary>
        <div className="preparation-options">
          {projection.evidence_claims.map((claim) => (
            <article key={claim.id} className="preparation-option">
              <strong>{claim.claim}</strong>
              <code>{claim.id}</code>
              <p>{claim.population} · {claim.study_design}</p>
              <p>
                Strength {claim.evidence_strength} · athlete applicability{" "}
                {claim.athlete_applicability}
              </p>
              <p>{claim.applicability_notes}</p>
              <p><strong>Uncertainty:</strong> {claim.uncertainty}</p>
              <p className="form-help">
                {claim.source_identifiers.map((item) => `${item.scheme}:${item.value}`).join(" · ")}
                {" · "}{claim.claim_version}
              </p>
            </article>
          ))}
        </div>
      </details>
      <p className="form-help">
        This projection contains no candidate relevance, trainability, transfer, fatigue, time, or
        interference scores. Those remain explicit reviewed inputs.
      </p>
    </section>
  );
}

function ReviewPreview({ draft }: { draft: OperatorInitialStrategyRequest }) {
  return (
    <section className="review-preview" aria-labelledby="review-preview-title">
      <header>
        <div>
          <p className="eyebrow">Parsed review document</p>
          <h2 id="review-preview-title">Inspect exact governed inputs</h2>
        </div>
        <span className="status-badge">{draft.candidate_contexts.length} candidate(s)</span>
      </header>
      <dl className="review-metadata">
        <div>
          <dt>Priority policy</dt>
          <dd>{draft.priority_policy_id}</dd>
        </div>
        <div>
          <dt>Exact policy review</dt>
          <dd>{draft.priority_policy_review_id}</dd>
        </div>
        <div>
          <dt>Generated at</dt>
          <dd>{new Date(draft.generated_at).toLocaleString()}</dd>
        </div>
        <div>
          <dt>Horizon / next review</dt>
          <dd>
            {draft.horizon_months} months / {draft.review_after_days} days
          </dd>
        </div>
      </dl>
      <div className="review-candidates">
        {draft.candidate_contexts.map((candidate, index) => (
          <article key={candidate.adaptation_id} className="review-candidate">
            <header>
              <div>
                <p className="eyebrow">Candidate {index + 1}</p>
                <h3>{candidate.adaptation_id}</h3>
              </div>
              <span
                className={`status-badge${candidate.safe_to_train ? " status-badge--cleared" : " status-badge--held"}`}
              >
                {candidate.safe_to_train ? "Safe to train" : "Not authorized for training"}
              </span>
            </header>
            <dl className="review-lineage">
              <div>
                <dt>Capability estimate</dt>
                <dd>{candidate.capability_estimate_id}</dd>
              </div>
              <div>
                <dt>Competency floor</dt>
                <dd>{candidate.competency_floor_id}</dd>
              </div>
              <div>
                <dt>Exact floor review</dt>
                <dd>{candidate.competency_floor_review_id}</dd>
              </div>
            </dl>
            <dl className="review-scores">
              {scoreLabels.map(([field, label]) => (
                <div key={field}>
                  <dt>{label}</dt>
                  <dd>{candidate[field].toFixed(2)}</dd>
                </div>
              ))}
            </dl>
            <p className="form-help">
              {candidate.source_observation_ids.length} source observation(s) ·{" "}
              {candidate.evidence_claim_ids.length} evidence claim(s) ·{" "}
              {candidate.prerequisite_adaptation_ids.length} prerequisite(s)
            </p>
            <ul className="review-flags" aria-label={`Candidate ${index + 1} review flags`}>
              <li>{candidate.prerequisites_met ? "Prerequisites met" : "Prerequisites missing"}</li>
              <li>
                {candidate.introductory_exposure_needed
                  ? "Introductory exposure needed"
                  : "No introductory exposure flag"}
              </li>
              <li>
                {candidate.cultivate_comparative_advantage
                  ? "Cultivate comparative advantage"
                  : "No comparative-advantage flag"}
              </li>
            </ul>
          </article>
        ))}
      </div>
      <section className="review-rationale" aria-label="Review rationale and uncertainty">
        <div>
          <h3>Applicability rationale</h3>
          <p>{draft.applicability_rationale}</p>
        </div>
        <div>
          <h3>Known uncertainty</h3>
          <p>{draft.uncertainty}</p>
        </div>
      </section>
    </section>
  );
}

function CreationReceipt({ result }: { result: InitialStrategyCreationResult }) {
  return (
    <section className="review-receipt" aria-labelledby="review-receipt-title">
      <p className="eyebrow">Strategy created</p>
      <h2 id="review-receipt-title">The reviewed decision is now immutable.</h2>
      <p>{result.decision_record.decision}</p>
      <dl className="review-metadata">
        <div>
          <dt>Strategy</dt>
          <dd>{result.strategy.id}</dd>
        </div>
        <div>
          <dt>Decision audit</dt>
          <dd>{result.decision_record.id}</dd>
        </div>
        <div>
          <dt>Next review</dt>
          <dd>{new Date(result.strategy.next_review_at).toLocaleString()}</dd>
        </div>
        <div>
          <dt>Rule</dt>
          <dd>{result.strategy.rule_version}</dd>
        </div>
      </dl>
      <p className="review-receipt__reason">{result.decision_record.reason}</p>
      <ul className="review-priorities">
        {result.strategy.priorities.map((priority) => (
          <li key={priority.id}>
            <strong>#{priority.rank} · {priority.state}</strong>
            <span>{priority.adaptation_id}</span>
            <span>
              Score {priority.score.toFixed(3)} · allocation {Math.round(priority.development_allocation * 100)}%
            </span>
          </li>
        ))}
      </ul>
      <details>
        <summary>Authority and evidence audit</summary>
        <ul>
          {result.decision_record.evidence.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </details>
      <Link
        href={`/review/resource-demands?strategyId=${encodeURIComponent(result.strategy.id)}`}
        className="primary-button"
      >
        Continue to resource-demand review
      </Link>
    </section>
  );
}

function InitialPlanningReviewContent() {
  const searchParams = useSearchParams();
  const [athleteId, setAthleteId] = useState(() => searchParams.get("athleteId") ?? "");
  const [documentText, setDocumentText] = useState("");
  const [draft, setDraft] = useState<OperatorInitialStrategyRequest | null>(null);
  const [preparation, setPreparation] =
    useState<InitialPlanningPreparationProjection | null>(null);
  const [preparationState, setPreparationState] = useState<"idle" | "loading">("idle");
  const [confirmed, setConfirmed] = useState(false);
  const [state, setState] = useState<"editing" | "submitting" | "created">("editing");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<InitialStrategyCreationResult | null>(null);

  async function loadPreparation() {
    const normalizedAthleteId = athleteId.trim();
    setMessage("");
    setPreparation(null);
    setDraft(null);
    if (!isUuid(normalizedAthleteId)) {
      setMessage("Enter a valid athlete UUID before loading preparation inputs.");
      return;
    }
    setPreparationState("loading");
    try {
      setPreparation(
        await fetchInitialPlanningPreparation(apiBaseUrl, normalizedAthleteId),
      );
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Unable to load initial-planning preparation.",
      );
    } finally {
      setPreparationState("idle");
    }
  }

  function inspectDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setResult(null);
    setConfirmed(false);
    if (!isUuid(athleteId.trim())) {
      setDraft(null);
      setMessage("Enter the UUID of the athlete whose first strategy is under review.");
      return;
    }
    if (preparation && preparation.status !== "planning_context_review_required") {
      setDraft(null);
      setMessage(preparation.message);
      return;
    }
    try {
      setDraft(parseInitialStrategyDraft(documentText));
    } catch (error) {
      setDraft(null);
      setMessage(error instanceof Error ? error.message : "Unable to parse the review document.");
    }
  }

  async function createStrategy() {
    if (!draft || !confirmed) {
      return;
    }
    setState("submitting");
    setMessage("");
    try {
      const created = await submitInitialStrategy(apiBaseUrl, athleteId.trim(), draft);
      setResult(created);
      setState("created");
    } catch (error) {
      setState("editing");
      setMessage(error instanceof Error ? error.message : "Unable to create the strategy.");
    }
  }

  return (
    <main className="review-shell">
      <header className="review-topbar">
        <div>
          <p className="eyebrow">AGAS · Planning authority</p>
          <h1>Initial strategy review</h1>
          <p>
            Inspect explicit, version-pinned inputs before creating one athlete&apos;s first
            long-range strategy. This console never infers scores or reviewer identity.
          </p>
        </div>
        <nav className="review-route-links" aria-label="Reviewer routes">
          <Link href="/review/queue" className="text-link">Queue</Link>
          <Link href="/review/resource-demands" className="text-link">Resource demands</Link>
          <Link href="/review/blocks" className="text-link">Blocks</Link>
          <Link href="/review/post-block" className="text-link">Post-block</Link>
          <Link href="/" className="text-link">Athlete PWA</Link>
        </nav>
      </header>

      <aside className="review-boundary" aria-label="Reviewer authority boundary">
        <strong>Permission is not a credential.</strong>
        <span>
          Submission requires the configured account&apos;s active planning-reviewer role. The server
          supplies the reviewer identity and exact role grant; this screen cannot override them.
        </span>
      </aside>

      {state === "created" && result ? <CreationReceipt result={result} /> : (
        <>
          <form className="review-input" onSubmit={inspectDocument}>
            <section>
              <label htmlFor="review-athlete-id">Athlete ID</label>
              <input
                id="review-athlete-id"
                value={athleteId}
                onChange={(event) => {
                  setAthleteId(event.target.value);
                  setDraft(null);
                  setPreparation(null);
                }}
                placeholder="00000000-0000-4000-8000-000000000000"
                autoComplete="off"
              />
              <button
                type="button"
                className="secondary-button preparation-load"
                disabled={preparationState === "loading"}
                onClick={() => void loadPreparation()}
              >
                {preparationState === "loading" ? "Loading eligible inputs…" : "Load eligible inputs"}
              </button>
            </section>
            {preparation ? <PreparationContext projection={preparation} /> : null}
            <details className="legacy-review-input">
              <summary>Legacy reviewed-JSON fallback</summary>
              <section>
                <label htmlFor="review-document">Reviewed initial-planning JSON</label>
                <textarea
                  id="review-document"
                  value={documentText}
                  onChange={(event) => {
                    setDocumentText(event.target.value);
                    setDraft(null);
                  }}
                  rows={18}
                  spellCheck={false}
                  placeholder="Paste an externally prepared document containing exact policy, review, candidate-context, provenance, rationale, and uncertainty fields."
                />
                <p className="form-help">
                  Transitional compatibility only. Do not include <code>reviewed_by</code> or{" "}
                  <code>review_authority_assignment_id</code>; the server owns them.
                </p>
                <button type="submit" className="primary-button">Parse and inspect JSON</button>
              </section>
            </details>
          </form>

          {preparation?.status === "planning_context_review_required" ? (
            <GovernedContextWorkflow
              apiBaseUrl={apiBaseUrl}
              athleteId={athleteId.trim()}
              projection={preparation}
              onCreated={(created) => {
                setResult(created);
                setState("created");
              }}
            />
          ) : null}

          {message ? <p className="form-error review-message" role="alert">{message}</p> : null}
          {draft ? (
            <>
              <ReviewPreview draft={draft} />
              <section className="review-confirmation">
                <label>
                  <input
                    type="checkbox"
                    checked={confirmed}
                    onChange={(event) => setConfirmed(event.target.checked)}
                  />
                  <span>
                    I reviewed the exact policy and floor review IDs, candidate scores, athlete
                    applicability, provenance, and stated uncertainty shown above.
                  </span>
                </label>
                <button
                  type="button"
                  className="primary-button"
                  disabled={!confirmed || state === "submitting"}
                  onClick={() => void createStrategy()}
                >
                  {state === "submitting" ? "Creating immutable strategy…" : "Create initial strategy"}
                </button>
                <p className="form-help">
                  This creates capability needs, one root strategy, and its decision audit in a
                  single transaction. It does not create a block or workout.
                </p>
              </section>
            </>
          ) : null}
        </>
      )}
    </main>
  );
}

export default function InitialPlanningReviewPage() {
  return (
    <Suspense fallback={<main className="review-shell"><p>Loading initial-planning review…</p></main>}>
      <InitialPlanningReviewContent />
    </Suspense>
  );
}
