"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  fetchBlockReviewPreparation,
  fetchPostBlockReviewQueue,
  fetchReplanningPreparation,
  isUuid,
  submitBlockReview,
  submitReplanning,
  type BlockReviewCreationResult,
  type BlockReviewPreparationProjection,
  type ComparisonDirection,
  type OperatorBlockReviewRequest,
  type OperatorReplanningRequest,
  type PostBlockReviewQueueItem,
  type PostBlockReviewQueueProjection,
  type PostBlockReplanningResult,
  type ReplanningCandidateContext,
  type ReplanningPreparationProjection,
} from "@/lib/post-block-review";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type BooleanSelection = "" | "true" | "false";

interface ResponseEditor {
  adaptationId: string;
  prescriptionIds: string[];
  baselineEstimateId: string;
  followupEstimateId: string;
  interventionSummary: string;
  measurementUncertainty: string;
  contextualFactors: string;
  comparisonDirection: "" | ComparisonDirection;
  minimumMeaningfulChange: string;
}

interface CandidateEditor {
  adaptationId: string;
  estimateId: string;
  floorId: string;
  generalRelevance: string;
  goalRelevance: string;
  prerequisiteValue: string;
  expectedTrainability: string;
  transferValue: string;
  fatigueCost: string;
  timeCost: string;
  interferenceCost: string;
  safeToTrain: BooleanSelection;
  introductoryExposureNeeded: BooleanSelection;
  prerequisitesMet: BooleanSelection;
  cultivateComparativeAdvantage: BooleanSelection;
  prerequisiteAdaptationIds: string;
  sourceObservationIds: string[];
  evidenceClaimIds: string[];
}

const scoreFields: Array<[keyof CandidateEditor, string]> = [
  ["generalRelevance", "General relevance"],
  ["goalRelevance", "Goal relevance"],
  ["prerequisiteValue", "Prerequisite value"],
  ["expectedTrainability", "Expected trainability"],
  ["transferValue", "Transfer value"],
  ["fatigueCost", "Fatigue cost"],
  ["timeCost", "Time cost"],
  ["interferenceCost", "Interference cost"],
];

function label(value: string): string {
  return value.replaceAll("_", " ");
}

function displayValue(value: unknown): string {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function lines(value: string): string[] {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

function PostBlockWorkQueue({
  projection,
  loading,
  onRefresh,
  onOpen,
}: {
  projection: PostBlockReviewQueueProjection | null;
  loading: boolean;
  onRefresh: () => void;
  onOpen: (item: PostBlockReviewQueueItem) => void;
}) {
  return (
    <section className="post-block-queue" aria-labelledby="post-block-queue-title">
      <header>
        <div>
          <p className="eyebrow">Derived reviewer work queue</p>
          <h2 id="post-block-queue-title">Blocks needing attention</h2>
          <p>Due work is reconstructed from immutable block, execution, review, and strategy history.</p>
        </div>
        <button type="button" className="secondary-button" disabled={loading} onClick={onRefresh}>
          {loading ? "Refreshing…" : "Refresh queue"}
        </button>
      </header>
      {!projection && loading ? <p className="form-help">Loading due review work…</p> : null}
      {projection && !projection.items.length ? (
        <p className="post-block-queue-empty">No completed block currently requires review or replanning.</p>
      ) : null}
      {projection?.items.length ? (
        <div className="post-block-queue-items">
          {projection.items.map((item) => {
            const ready = item.status.startsWith("ready_for_");
            return (
              <article key={`${item.workflow_stage}:${item.block_id}`}>
                <header>
                  <div>
                    <strong>{item.athlete_display_name}</strong>
                    <span>{item.block_starts_on}–{item.block_ends_on}</span>
                  </div>
                  <span className={`status-badge status-badge--${item.status}`}>
                    {ready ? "Ready" : "Blocked"}
                  </span>
                </header>
                <p>{item.block_hypothesis}</p>
                <dl>
                  <div><dt>Stage</dt><dd>{label(item.workflow_stage)}</dd></div>
                  {item.review_outcome ? <div><dt>Review outcome</dt><dd>{label(item.review_outcome)}</dd></div> : null}
                </dl>
                {item.issues.length ? (
                  <details>
                    <summary>{item.issues.length} blocking issue(s)</summary>
                    <ul>{item.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul>
                  </details>
                ) : null}
                <button type="button" className={ready ? "primary-button" : "secondary-button"} onClick={() => onOpen(item)}>
                  {item.workflow_stage === "block_review" ? "Open block history" : "Open replanning review"}
                </button>
              </article>
            );
          })}
        </div>
      ) : null}
      {projection ? (
        <p className="form-help">Projected {new Date(projection.projected_at).toLocaleString()} · {projection.projection_version}</p>
      ) : null}
    </section>
  );
}

function requiredNumber(value: string, field: string): number {
  if (!value.trim()) throw new Error(`${field} is required.`);
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) throw new Error(`${field} must be numeric.`);
  return parsed;
}

function requiredBoolean(value: BooleanSelection, field: string): boolean {
  if (!value) throw new Error(`${field} requires an explicit yes or no.`);
  return value === "true";
}

function emptyResponse(): ResponseEditor {
  return {
    adaptationId: "",
    prescriptionIds: [],
    baselineEstimateId: "",
    followupEstimateId: "",
    interventionSummary: "",
    measurementUncertainty: "",
    contextualFactors: "",
    comparisonDirection: "",
    minimumMeaningfulChange: "",
  };
}

function emptyCandidate(adaptationId: string): CandidateEditor {
  return {
    adaptationId,
    estimateId: "",
    floorId: "",
    generalRelevance: "",
    goalRelevance: "",
    prerequisiteValue: "",
    expectedTrainability: "",
    transferValue: "",
    fatigueCost: "",
    timeCost: "",
    interferenceCost: "",
    safeToTrain: "",
    introductoryExposureNeeded: "",
    prerequisitesMet: "",
    cultivateComparativeAdvantage: "",
    prerequisiteAdaptationIds: "",
    sourceObservationIds: [],
    evidenceClaimIds: [],
  };
}

function BlockPreparation({ projection }: { projection: BlockReviewPreparationProjection }) {
  const completed = projection.session_history.filter((item) => item.execution).length;
  const safetyClosed = projection.session_history.filter(
    (item) => item.post_session_safety_decisions.length > 0,
  ).length;
  return (
    <section className="review-preparation post-block-preparation">
      <header>
        <div>
          <p className="eyebrow">Completed-history preparation</p>
          <h2>Block {projection.block.starts_on}–{projection.block.ends_on}</h2>
          <p>{projection.block.hypothesis}</p>
        </div>
        <span className={`status-badge status-badge--${projection.status}`}>
          {label(projection.status)}
        </span>
      </header>
      <dl className="review-metadata">
        <div><dt>Persisted weeks</dt><dd>{projection.weekly_plans.length}/{projection.block.duration_weeks}</dd></div>
        <div><dt>Execution outcomes</dt><dd>{completed}/{projection.session_history.length}</dd></div>
        <div><dt>Safety-closed sessions</dt><dd>{safetyClosed}/{projection.session_history.length}</dd></div>
        <div><dt>Review policies</dt><dd>{projection.block_review_policies.length}</dd></div>
      </dl>
      {projection.issues.length ? (
        <ul className="post-block-issues">
          {projection.issues.map((issue) => <li key={issue}>{issue}</li>)}
        </ul>
      ) : null}
      <details open>
        <summary>Delivered session history</summary>
        <div className="post-block-history">
          {projection.session_history.map((history) => (
            <article key={history.planned_session.id}>
              <strong>{history.session_template.name}</strong>
              <span>{new Date(history.planned_session.starts_at).toLocaleString()}</span>
              <span>
                {history.execution ? label(history.execution.status) : "no execution"} ·{" "}
                {history.adherences.length} adherence record(s) ·{" "}
                {history.post_session_safety_decisions.length} safety decision(s)
              </span>
              <code>{history.planned_session.id}</code>
            </article>
          ))}
        </div>
      </details>
      <div className="post-block-estimate-columns">
        <section>
          <h3>Eligible baselines</h3>
          {projection.baseline_estimates.map((estimate) => (
            <article key={estimate.id} className="post-block-estimate">
              <strong>{label(estimate.domain)} · {displayValue(estimate.estimate)} {estimate.unit_or_scale}</strong>
              <span>{estimate.estimate_scope} · {estimate.confidence} · {estimate.rule_version}</span>
              <code>{estimate.id}</code>
            </article>
          ))}
        </section>
        <section>
          <h3>Eligible follow-ups</h3>
          {projection.followup_estimates.map((estimate) => (
            <article key={estimate.id} className="post-block-estimate">
              <strong>{label(estimate.domain)} · {displayValue(estimate.estimate)} {estimate.unit_or_scale}</strong>
              <span>{estimate.estimate_scope} · {estimate.confidence} · {estimate.rule_version}</span>
              <code>{estimate.id}</code>
            </article>
          ))}
        </section>
      </div>
      <details>
        <summary>{projection.source_observations.length} source observation(s) and {projection.evidence_claims.length} evidence claim(s)</summary>
        <div className="post-block-provenance">
          {projection.source_observations.map((observation) => (
            <article key={observation.id}>
              <strong>{observation.observation_type}</strong>
              <span>{displayValue(observation.measurement)} {observation.unit ?? ""} · {observation.reliability}</span>
              <code>{observation.id}</code>
            </article>
          ))}
          {projection.evidence_claims.map((claim) => (
            <article key={claim.id}>
              <strong>{claim.claim}</strong>
              <span>{claim.evidence_strength} evidence · {claim.athlete_applicability} applicability</span>
              <code>{claim.id}</code>
            </article>
          ))}
        </div>
      </details>
      <p className="form-help">
        Preparation reports eligible history only. It does not group prescriptions, choose a
        meaningful-change threshold, or interpret causality.
      </p>
    </section>
  );
}

function BlockReviewReceipt({
  result,
  onContinue,
}: {
  result: BlockReviewCreationResult;
  onContinue: (reviewId: string) => void;
}) {
  return (
    <section className="review-receipt post-block-receipt">
      <p className="eyebrow">Immutable block review</p>
      <h2>{label(result.block_review.outcome)}</h2>
      <p>{result.decision_record.decision}</p>
      <dl className="review-metadata">
        <div><dt>Review</dt><dd>{result.block_review.id}</dd></div>
        <div><dt>Adherence</dt><dd>{Math.round(result.block_review.aggregate_adherence_ratio * 100)}%</dd></div>
        <div><dt>Delivered prescription items</dt><dd>{result.block_review.completed_item_count}/{result.block_review.prescribed_item_count}</dd></div>
        <div><dt>Decision audit</dt><dd>{result.decision_record.id}</dd></div>
      </dl>
      <div className="post-block-responses">
        {result.training_responses.map((response) => {
          const evaluation = result.block_review.response_evaluations.find(
            (item) => item.training_response_id === response.id,
          );
          return (
            <article key={response.id}>
              <strong>{response.observed_change >= 0 ? "+" : ""}{response.observed_change} estimate-unit change</strong>
              <span>{response.completed_item_count}/{response.prescribed_item_count} items delivered · {Math.round(response.adherence_ratio * 100)}% adherence · {response.confidence}</span>
              <span>{evaluation?.rationale}</span>
              <code>{response.id}</code>
            </article>
          );
        })}
      </div>
      <p className="review-receipt__reason">{result.decision_record.reason}</p>
      <details>
        <summary>Authority and evidence audit</summary>
        <ul>{result.decision_record.evidence.map((item) => <li key={item}>{item}</li>)}</ul>
      </details>
      <button className="primary-button" type="button" onClick={() => onContinue(result.block_review.id)}>
        Prepare response-dependent replanning
      </button>
    </section>
  );
}

function BlockReviewForm({
  projection,
  onCreated,
}: {
  projection: BlockReviewPreparationProjection;
  onCreated: (result: BlockReviewCreationResult) => void;
}) {
  const [responses, setResponses] = useState<ResponseEditor[]>([emptyResponse()]);
  const [policyId, setPolicyId] = useState("");
  const [applicability, setApplicability] = useState("");
  const [uncertainty, setUncertainty] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const assignedIds = responses.flatMap((response) => response.prescriptionIds);

  function update(index: number, patch: Partial<ResponseEditor>) {
    setResponses((current) => current.map((item, itemIndex) => (
      itemIndex === index ? { ...item, ...patch } : item
    )));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!confirmed) return;
    setBusy(true);
    setMessage("");
    try {
      const expected = new Set(projection.prescriptions.map((item) => item.id));
      const actual = new Set(assignedIds);
      if (actual.size !== expected.size || [...expected].some((id) => !actual.has(id))) {
        throw new Error("Every prepared prescription must be assigned exactly once.");
      }
      for (const [index, response] of responses.entries()) {
        const mismatched = response.prescriptionIds.some((id) => (
          projection.prescriptions.find((item) => item.id === id)?.adaptation_id
          !== response.adaptationId
        ));
        if (mismatched) throw new Error(`Response ${index + 1} contains a prescription for another adaptation.`);
      }
      const instant = new Date().toISOString();
      const request: OperatorBlockReviewRequest = {
        block_review_policy_id: policyId,
        response_drafts: responses.map((response, index) => {
          if (!response.comparisonDirection) {
            throw new Error(`Response ${index + 1} comparison direction is required.`);
          }
          return {
            adaptation_id: response.adaptationId,
            prescription_ids: response.prescriptionIds,
            baseline_capability_estimate_id: response.baselineEstimateId,
            followup_capability_estimate_id: response.followupEstimateId,
            intervention_summary: response.interventionSummary,
            measurement_uncertainty: response.measurementUncertainty,
            contextual_factors: lines(response.contextualFactors),
            comparison_direction: response.comparisonDirection,
            minimum_meaningful_change: requiredNumber(
              response.minimumMeaningfulChange,
              `Response ${index + 1} meaningful change`,
            ),
          };
        }),
        responses_calculated_at: instant,
        reviewed_at: instant,
        applicability_rationale: applicability,
        uncertainty,
      };
      onCreated(await submitBlockReview(apiBaseUrl, projection.block.id, request));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to persist the block review.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="governed-context post-block-form" onSubmit={submit}>
      <header>
        <div>
          <p className="eyebrow">Explicit response interpretation</p>
          <h2>Group delivered prescriptions</h2>
          <p>Each prescription must appear exactly once. Adaptation, estimates, comparison direction, and threshold remain reviewer choices.</p>
        </div>
        <span className="status-badge">{new Set(assignedIds).size}/{projection.prescriptions.length} assigned</span>
      </header>

      <section className="resource-section">
        <h3>Block-review policy</h3>
        <div className="post-block-policy-grid">
          {projection.block_review_policies.map((policy) => (
            <label key={policy.id}>
              <input type="radio" name="block-policy" checked={policyId === policy.id} onChange={() => setPolicyId(policy.id)} />
              <span>
                <strong>{policy.policy_version}</strong>
                <small>Minimum adherence {Math.round(policy.minimum_adherence_ratio * 100)}% · minimum confidence {policy.minimum_response_confidence}</small>
                <small>{policy.rationale}</small>
                <code>{policy.id}</code>
              </span>
            </label>
          ))}
        </div>
      </section>

      <div className="post-block-response-editors">
        {responses.map((response, index) => (
          <fieldset key={index} className="post-block-response-editor">
            <legend>Response interpretation {index + 1}</legend>
            <div className="post-block-field-grid">
              <label>
                Adaptation
                <select value={response.adaptationId} onChange={(event) => update(index, { adaptationId: event.target.value, prescriptionIds: [] })} required>
                  <option value="">Select explicitly</option>
                  {[...new Map(projection.prescriptions.map((item) => [item.adaptation_id, item])).keys()].map((id) => <option key={id} value={id}>{id}</option>)}
                </select>
              </label>
              <label>
                Baseline estimate
                <select value={response.baselineEstimateId} onChange={(event) => update(index, { baselineEstimateId: event.target.value, followupEstimateId: "" })} required>
                  <option value="">Select explicitly</option>
                  {projection.baseline_estimates.map((estimate) => <option key={estimate.id} value={estimate.id}>{label(estimate.domain)} · {displayValue(estimate.estimate)} {estimate.unit_or_scale} · {estimate.estimate_scope}</option>)}
                </select>
              </label>
              <label>
                Follow-up estimate
                <select value={response.followupEstimateId} onChange={(event) => update(index, { followupEstimateId: event.target.value })} required>
                  <option value="">{response.baselineEstimateId ? "Select explicitly" : "Select a baseline first"}</option>
                  {projection.followup_estimates.filter((estimate) => {
                    const baseline = projection.baseline_estimates.find((item) => item.id === response.baselineEstimateId);
                    return baseline
                      && estimate.domain === baseline.domain
                      && estimate.estimate_scope === baseline.estimate_scope
                      && estimate.unit_or_scale === baseline.unit_or_scale;
                  }).map((estimate) => <option key={estimate.id} value={estimate.id}>{label(estimate.domain)} · {displayValue(estimate.estimate)} {estimate.unit_or_scale} · {estimate.estimate_scope}</option>)}
                </select>
              </label>
              <label>
                Comparison direction
                <select value={response.comparisonDirection} onChange={(event) => update(index, { comparisonDirection: event.target.value as ResponseEditor["comparisonDirection"] })} required>
                  <option value="">Select explicitly</option>
                  <option value="higher_is_better">Higher is better</option>
                  <option value="lower_is_better">Lower is better</option>
                </select>
              </label>
              <label>
                Minimum meaningful change
                <input type="number" min="0" step="any" value={response.minimumMeaningfulChange} onChange={(event) => update(index, { minimumMeaningfulChange: event.target.value })} required />
              </label>
            </div>
            <section className="post-block-prescription-selection">
              <h4>Prescription partition</h4>
              {projection.prescriptions.map((prescription) => {
                const selectedElsewhere = assignedIds.includes(prescription.id) && !response.prescriptionIds.includes(prescription.id);
                const wrongAdaptation = Boolean(response.adaptationId)
                  && prescription.adaptation_id !== response.adaptationId;
                return (
                  <label key={prescription.id}>
                    <input
                      type="checkbox"
                      checked={response.prescriptionIds.includes(prescription.id)}
                      disabled={selectedElsewhere || wrongAdaptation}
                      onChange={(event) => update(index, {
                        prescriptionIds: event.target.checked
                          ? [...response.prescriptionIds, prescription.id]
                          : response.prescriptionIds.filter((id) => id !== prescription.id),
                      })}
                    />
                    <span>
                      <strong>{prescription.sets} × {prescription.repetitions_per_set ?? `${prescription.duration_seconds}s`} · {prescription.planned_duration_minutes} min</strong>
                      <small>{prescription.reason_for_inclusion}</small>
                      <small>Adaptation {prescription.adaptation_id}</small>
                      <code>{prescription.id}</code>
                    </span>
                  </label>
                );
              })}
            </section>
            <label>Intervention summary<textarea rows={3} value={response.interventionSummary} onChange={(event) => update(index, { interventionSummary: event.target.value })} required /></label>
            <label>Measurement uncertainty<textarea rows={3} value={response.measurementUncertainty} onChange={(event) => update(index, { measurementUncertainty: event.target.value })} required /></label>
            <label>Contextual factors <span>One per line; may be empty.</span><textarea rows={3} value={response.contextualFactors} onChange={(event) => update(index, { contextualFactors: event.target.value })} /></label>
            {responses.length > 1 ? <button type="button" className="secondary-button" onClick={() => setResponses((current) => current.filter((_, itemIndex) => itemIndex !== index))}>Remove response</button> : null}
          </fieldset>
        ))}
      </div>
      <button type="button" className="secondary-button" onClick={() => setResponses((current) => [...current, emptyResponse()])}>Add response interpretation</button>
      <section className="post-block-review-rationale">
        <label>Applicability rationale<textarea rows={4} value={applicability} onChange={(event) => setApplicability(event.target.value)} required /></label>
        <label>Known uncertainty<textarea rows={4} value={uncertainty} onChange={(event) => setUncertainty(event.target.value)} required /></label>
      </section>
      <label className="review-confirmation-line">
        <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
        <span>I reviewed the exact delivered-history partition, comparable estimates, policy, thresholds, applicability, and uncertainty.</span>
      </label>
      <button className="primary-button" disabled={!confirmed || busy}>
        {busy ? "Persisting immutable review…" : "Create block review"}
      </button>
      <p className="form-help">The server derives responses and the review atomically. This form does not update athlete state or generate the next strategy.</p>
      {message ? <p className="form-error" role="alert">{message}</p> : null}
    </form>
  );
}

function ReplanningPreparation({ projection }: { projection: ReplanningPreparationProjection }) {
  return (
    <section className="review-preparation post-block-preparation">
      <header>
        <div>
          <p className="eyebrow">Response-dependent preparation</p>
          <h2>{label(projection.block_review.outcome)} review</h2>
          <p>Prior strategy {projection.previous_strategy.id} remains immutable. Every successor context below must be reviewed explicitly.</p>
        </div>
        <span className={`status-badge status-badge--${projection.status}`}>{label(projection.status)}</span>
      </header>
      {projection.issues.length ? <ul className="post-block-issues">{projection.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul> : null}
      <div className="post-block-option-grid">
        {projection.adaptation_options.map((option) => (
          <article key={option.adaptation.id}>
            <strong>#{option.previous_priority.rank} · {option.adaptation.name}</strong>
            <span>{label(option.previous_priority.state)} · {label(option.adaptation.domain)}</span>
            <span>{option.estimate_options.length} eligible estimate(s) · {option.compatible_competency_floors.length} compatible floor(s)</span>
            {option.training_response ? <span>Reviewed change {option.training_response.observed_change >= 0 ? "+" : ""}{option.training_response.observed_change} · {Math.round(option.training_response.adherence_ratio * 100)}% adherence</span> : null}
            <code>{option.adaptation.id}</code>
          </article>
        ))}
      </div>
      <p className="form-help">For an actively trained adaptation, the eligible estimate set contains only its reviewed follow-up. Eligibility does not choose its floor or planning score.</p>
    </section>
  );
}

function StrategyReceipt({ result }: { result: PostBlockReplanningResult }) {
  return (
    <section className="review-receipt post-block-receipt">
      <p className="eyebrow">Successor strategy appended</p>
      <h2>Response history changed the planning state.</h2>
      <p>{result.decision_record.decision}</p>
      <dl className="review-metadata">
        <div><dt>Successor strategy</dt><dd>{result.strategy.id}</dd></div>
        <div><dt>Prior strategy</dt><dd>{result.strategy.supersedes_strategy_id}</dd></div>
        <div><dt>Triggering review</dt><dd>{result.strategy.triggering_block_review_id}</dd></div>
        <div><dt>Next review</dt><dd>{new Date(result.strategy.next_review_at).toLocaleString()}</dd></div>
      </dl>
      <ul className="review-priorities">
        {result.strategy.priorities.map((priority) => (
          <li key={priority.id}>
            <strong>#{priority.rank} · {label(priority.state)}</strong>
            <span>{priority.adaptation_id}</span>
            <span>Score {priority.score.toFixed(3)} · allocation {Math.round(priority.development_allocation * 100)}%</span>
          </li>
        ))}
      </ul>
      <p className="review-receipt__reason">{result.decision_record.reason}</p>
      <details><summary>Authority and evidence audit</summary><ul>{result.decision_record.evidence.map((item) => <li key={item}>{item}</li>)}</ul></details>
      <Link className="primary-button" href={`/review/resource-demands?strategyId=${encodeURIComponent(result.strategy.id)}`}>Prepare the successor block</Link>
    </section>
  );
}

function ReplanningForm({
  projection,
  onCreated,
}: {
  projection: ReplanningPreparationProjection;
  onCreated: (result: PostBlockReplanningResult) => void;
}) {
  const [candidates, setCandidates] = useState<CandidateEditor[]>(
    () => projection.adaptation_options.map((option) => emptyCandidate(option.adaptation.id)),
  );
  const [reviewAfterDays, setReviewAfterDays] = useState("");
  const [applicability, setApplicability] = useState("");
  const [uncertainty, setUncertainty] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  function update(index: number, patch: Partial<CandidateEditor>) {
    setCandidates((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  }

  function toggleId(index: number, field: "sourceObservationIds" | "evidenceClaimIds", id: string, checked: boolean) {
    const values = candidates[index][field];
    update(index, { [field]: checked ? [...values, id] : values.filter((item) => item !== id) });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!confirmed) return;
    setBusy(true);
    setMessage("");
    try {
      const contexts: ReplanningCandidateContext[] = candidates.map((candidate, index) => ({
        adaptation_id: candidate.adaptationId,
        competency_floor_id: candidate.floorId,
        capability_estimate_id: candidate.estimateId,
        general_relevance: requiredNumber(candidate.generalRelevance, `Candidate ${index + 1} general relevance`),
        goal_relevance: requiredNumber(candidate.goalRelevance, `Candidate ${index + 1} goal relevance`),
        prerequisite_value: requiredNumber(candidate.prerequisiteValue, `Candidate ${index + 1} prerequisite value`),
        expected_trainability: requiredNumber(candidate.expectedTrainability, `Candidate ${index + 1} expected trainability`),
        transfer_value: requiredNumber(candidate.transferValue, `Candidate ${index + 1} transfer value`),
        fatigue_cost: requiredNumber(candidate.fatigueCost, `Candidate ${index + 1} fatigue cost`),
        time_cost: requiredNumber(candidate.timeCost, `Candidate ${index + 1} time cost`),
        interference_cost: requiredNumber(candidate.interferenceCost, `Candidate ${index + 1} interference cost`),
        safe_to_train: requiredBoolean(candidate.safeToTrain, `Candidate ${index + 1} safety`),
        introductory_exposure_needed: requiredBoolean(candidate.introductoryExposureNeeded, `Candidate ${index + 1} introductory exposure`),
        prerequisites_met: requiredBoolean(candidate.prerequisitesMet, `Candidate ${index + 1} prerequisites`),
        prerequisite_adaptation_ids: lines(candidate.prerequisiteAdaptationIds),
        cultivate_comparative_advantage: requiredBoolean(candidate.cultivateComparativeAdvantage, `Candidate ${index + 1} comparative advantage`),
        source_observation_ids: candidate.sourceObservationIds,
        evidence_claim_ids: candidate.evidenceClaimIds,
      }));
      const request: OperatorReplanningRequest = {
        candidate_contexts: contexts,
        generated_at: new Date().toISOString(),
        review_after_days: requiredNumber(reviewAfterDays, "Review interval"),
        applicability_rationale: applicability,
        uncertainty,
      };
      onCreated(await submitReplanning(apiBaseUrl, projection.block_review.id, request));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to append the successor strategy.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="governed-context post-block-form" onSubmit={submit}>
      <header>
        <div>
          <p className="eyebrow">Explicit successor contexts</p>
          <h2>Re-evaluate every prior adaptation</h2>
          <p>Scores are reviewed inputs, not suggested values. All eight components and four state flags begin unset.</p>
        </div>
        <span className="status-badge">{candidates.length} candidate(s)</span>
      </header>
      <div className="post-block-candidate-editors">
        {candidates.map((candidate, index) => {
          const option = projection.adaptation_options[index];
          const estimate = option.estimate_options.find((item) => item.id === candidate.estimateId);
          const floors = option.compatible_competency_floors.filter((floor) => (
            !estimate || (floor.estimate_scope === estimate.estimate_scope && floor.unit_or_scale === estimate.unit_or_scale)
          ));
          return (
            <fieldset key={candidate.adaptationId} className="post-block-candidate-editor">
              <legend>#{option.previous_priority.rank} · {option.adaptation.name}</legend>
              <p className="form-help">Prior state {label(option.previous_priority.state)} · {label(option.adaptation.domain)} · adaptation <code>{option.adaptation.id}</code></p>
              <div className="post-block-field-grid">
                <label>
                  Capability estimate
                  <select value={candidate.estimateId} onChange={(event) => update(index, { estimateId: event.target.value, floorId: "" })} required>
                    <option value="">Select explicitly</option>
                    {option.estimate_options.map((item) => <option key={item.id} value={item.id}>{displayValue(item.estimate)} {item.unit_or_scale} · {item.estimate_scope} · {item.confidence}</option>)}
                  </select>
                </label>
                <label>
                  Competency floor
                  <select value={candidate.floorId} onChange={(event) => update(index, { floorId: event.target.value })} required>
                    <option value="">Select explicitly</option>
                    {floors.map((floor) => <option key={floor.id} value={floor.id}>{label(floor.comparison_direction)} {floor.threshold} {floor.unit_or_scale} · {floor.population}</option>)}
                  </select>
                </label>
              </div>
              <div className="post-block-score-grid">
                {scoreFields.map(([field, fieldLabel]) => (
                  <label key={field}>{fieldLabel}<input type="number" min="0" max="1" step="0.01" value={candidate[field] as string} onChange={(event) => update(index, { [field]: event.target.value })} required /></label>
                ))}
              </div>
              <div className="post-block-flag-grid">
                {([
                  ["safeToTrain", "Safe to train"],
                  ["introductoryExposureNeeded", "Introductory exposure needed"],
                  ["prerequisitesMet", "Prerequisites met"],
                  ["cultivateComparativeAdvantage", "Cultivate comparative advantage"],
                ] as Array<[keyof CandidateEditor, string]>).map(([field, fieldLabel]) => (
                  <label key={field}>{fieldLabel}<select value={candidate[field] as string} onChange={(event) => update(index, { [field]: event.target.value as BooleanSelection })} required><option value="">Select explicitly</option><option value="true">Yes</option><option value="false">No</option></select></label>
                ))}
              </div>
              <label>Prerequisite adaptation IDs <span>One UUID per line; may be empty.</span><textarea rows={3} value={candidate.prerequisiteAdaptationIds} onChange={(event) => update(index, { prerequisiteAdaptationIds: event.target.value })} /></label>
              <details>
                <summary>Optional context-specific provenance</summary>
                <div className="post-block-provenance-selectors">
                  <fieldset>
                    <legend>Observations</legend>
                    {projection.source_observations.map((observation) => <label key={observation.id}><input type="checkbox" checked={candidate.sourceObservationIds.includes(observation.id)} onChange={(event) => toggleId(index, "sourceObservationIds", observation.id, event.target.checked)} /><span>{observation.observation_type}<small>{observation.id}</small></span></label>)}
                  </fieldset>
                  <fieldset>
                    <legend>Evidence claims</legend>
                    {projection.evidence_claims.map((claim) => <label key={claim.id}><input type="checkbox" checked={candidate.evidenceClaimIds.includes(claim.id)} onChange={(event) => toggleId(index, "evidenceClaimIds", claim.id, event.target.checked)} /><span>{claim.claim}<small>{claim.id}</small></span></label>)}
                  </fieldset>
                </div>
              </details>
            </fieldset>
          );
        })}
      </div>
      <div className="post-block-field-grid">
        <label>Review again after (days)<input type="number" min="1" step="1" value={reviewAfterDays} onChange={(event) => setReviewAfterDays(event.target.value)} required /></label>
      </div>
      <section className="post-block-review-rationale">
        <label>Applicability rationale<textarea rows={4} value={applicability} onChange={(event) => setApplicability(event.target.value)} required /></label>
        <label>Known uncertainty<textarea rows={4} value={uncertainty} onChange={(event) => setUncertainty(event.target.value)} required /></label>
      </section>
      <label className="review-confirmation-line"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /><span>I reviewed every estimate, floor, score, prerequisite, safety flag, provenance choice, applicability statement, and uncertainty.</span></label>
      <button className="primary-button" disabled={!confirmed || busy}>{busy ? "Appending immutable successor…" : "Create successor strategy"}</button>
      <p className="form-help">The server rebuilds needs and scores the successor using the persisted policy. It preserves the prior strategy and review chain.</p>
      {message ? <p className="form-error" role="alert">{message}</p> : null}
    </form>
  );
}

export function PostBlockReviewClient({
  initialBlockId,
  initialBlockReviewId,
}: {
  initialBlockId: string;
  initialBlockReviewId: string;
}) {
  const [blockId, setBlockId] = useState(initialBlockId);
  const [blockReviewId, setBlockReviewId] = useState(initialBlockReviewId);
  const [blockPreparation, setBlockPreparation] = useState<BlockReviewPreparationProjection | null>(null);
  const [reviewResult, setReviewResult] = useState<BlockReviewCreationResult | null>(null);
  const [replanningPreparation, setReplanningPreparation] = useState<ReplanningPreparationProjection | null>(null);
  const [strategyResult, setStrategyResult] = useState<PostBlockReplanningResult | null>(null);
  const [queue, setQueue] = useState<PostBlockReviewQueueProjection | null>(null);
  const [queueLoading, setQueueLoading] = useState(true);
  const [queueMessage, setQueueMessage] = useState("");
  const [loading, setLoading] = useState<"" | "block" | "replanning">("");
  const [message, setMessage] = useState("");

  const refreshQueue = useCallback(async () => {
    setQueueLoading(true);
    setQueueMessage("");
    try {
      setQueue(await fetchPostBlockReviewQueue(apiBaseUrl));
    } catch (error) {
      setQueueMessage(error instanceof Error ? error.message : "Unable to load post-block work.");
    } finally {
      setQueueLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    fetchPostBlockReviewQueue(apiBaseUrl)
      .then((projection) => {
        if (active) setQueue(projection);
      })
      .catch((error: unknown) => {
        if (active) {
          setQueueMessage(
            error instanceof Error ? error.message : "Unable to load post-block work.",
          );
        }
      })
      .finally(() => {
        if (active) setQueueLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function loadBlock(idOverride?: string) {
    const id = (idOverride ?? blockId).trim();
    setMessage("");
    setBlockPreparation(null);
    setReviewResult(null);
    setReplanningPreparation(null);
    setStrategyResult(null);
    if (!isUuid(id)) return setMessage("Enter a valid block UUID.");
    setBlockId(id);
    setLoading("block");
    try {
      const projection = await fetchBlockReviewPreparation(apiBaseUrl, id);
      setBlockPreparation(projection);
      if (projection.existing_review) setBlockReviewId(projection.existing_review.id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load block-review preparation.");
    } finally {
      setLoading("");
    }
  }

  async function loadReplanning(idOverride?: string) {
    const id = (idOverride ?? blockReviewId).trim();
    setMessage("");
    setBlockPreparation(null);
    setReviewResult(null);
    setReplanningPreparation(null);
    setStrategyResult(null);
    if (!isUuid(id)) return setMessage("Enter a valid block-review UUID.");
    setBlockReviewId(id);
    setLoading("replanning");
    try {
      setReplanningPreparation(await fetchReplanningPreparation(apiBaseUrl, id));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load replanning preparation.");
    } finally {
      setLoading("");
    }
  }

  return (
    <main className="review-shell">
      <header className="review-topbar">
        <div>
          <p className="eyebrow">AGAS · Closed-loop planning authority</p>
          <h1>Post-block review</h1>
          <p>Close one fully observed block, inspect the derived response, then append a response-dependent successor strategy.</p>
        </div>
        <nav className="review-route-links" aria-label="Reviewer routes">
          <Link href="/review/queue" className="text-link">Queue</Link>
          <Link href="/review/weeks" className="text-link">Week 1</Link>
          <Link href="/review/blocks" className="text-link">Blocks</Link>
          <Link href="/" className="text-link">Athlete PWA</Link>
        </nav>
      </header>
      <aside className="review-boundary">
        <strong>Interpretation remains explicit.</strong>
        <span>The server owns reviewer identity, verifies complete history, derives response arithmetic, and preserves every predecessor. The browser supplies no hidden threshold or score.</span>
      </aside>
      <PostBlockWorkQueue
        projection={queue}
        loading={queueLoading}
        onRefresh={() => void refreshQueue()}
        onOpen={(item) => {
          if (item.workflow_stage === "block_review") void loadBlock(item.block_id);
          else if (item.block_review_id) void loadReplanning(item.block_review_id);
        }}
      />
      {queueMessage ? <p className="form-error review-message" role="alert">{queueMessage}</p> : null}
      <details className="post-block-manual-lookup">
        <summary>Manual ID lookup</summary>
        <section className="post-block-loaders">
          <label>Completed block ID<input value={blockId} onChange={(event) => setBlockId(event.target.value)} placeholder="00000000-0000-4000-8000-000000000000" /></label>
          <button type="button" className="secondary-button" disabled={loading === "block"} onClick={() => void loadBlock()}>{loading === "block" ? "Loading history…" : "Load block history"}</button>
          <span>or</span>
          <label>Existing block-review ID<input value={blockReviewId} onChange={(event) => setBlockReviewId(event.target.value)} placeholder="00000000-0000-4000-8000-000000000000" /></label>
          <button type="button" className="secondary-button" disabled={loading === "replanning"} onClick={() => void loadReplanning()}>{loading === "replanning" ? "Loading response…" : "Load replanning inputs"}</button>
        </section>
      </details>
      {message ? <p className="form-error review-message" role="alert">{message}</p> : null}
      {blockPreparation ? <BlockPreparation projection={blockPreparation} /> : null}
      {blockPreparation?.status === "ready_for_explicit_review" && !reviewResult ? <BlockReviewForm projection={blockPreparation} onCreated={(result) => { setReviewResult(result); setBlockReviewId(result.block_review.id); void refreshQueue(); }} /> : null}
      {blockPreparation?.status === "already_reviewed" && blockPreparation.existing_review && !replanningPreparation ? <button className="primary-button post-block-continue" type="button" onClick={() => void loadReplanning(blockPreparation.existing_review?.id)}>Continue from existing review</button> : null}
      {reviewResult ? <BlockReviewReceipt result={reviewResult} onContinue={(id) => void loadReplanning(id)} /> : null}
      {replanningPreparation ? <ReplanningPreparation projection={replanningPreparation} /> : null}
      {replanningPreparation?.status === "ready_for_explicit_replanning" && !strategyResult ? <ReplanningForm key={replanningPreparation.block_review.id} projection={replanningPreparation} onCreated={(result) => { setStrategyResult(result); void refreshQueue(); }} /> : null}
      {replanningPreparation?.status === "already_replanned" && replanningPreparation.existing_successor_strategy ? <section className="review-receipt"><p className="eyebrow">Already replanned</p><h2>Successor strategy is immutable.</h2><code>{replanningPreparation.existing_successor_strategy.id}</code><Link className="primary-button" href={`/review/resource-demands?strategyId=${encodeURIComponent(replanningPreparation.existing_successor_strategy.id)}`}>Open successor strategy</Link></section> : null}
      {strategyResult ? <StrategyReceipt result={strategyResult} /> : null}
    </main>
  );
}
