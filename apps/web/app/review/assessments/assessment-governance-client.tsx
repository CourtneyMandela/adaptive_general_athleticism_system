"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  fetchAssessmentGovernance,
  fetchAssessmentGovernanceCandidates,
  ratifyAssessmentGovernanceCandidate,
  type AssessmentGovernanceCandidateProjection,
  type AssessmentGovernanceProjection,
} from "@/lib/assessment-governance";
import type { EvidenceAuthorityEvaluation } from "@/lib/evidence-governance";
import { athleteHomeHref, athleteReviewHref } from "@/lib/athlete-navigation";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function label(value: string): string {
  return value.replaceAll("_", " ");
}

function EvidenceAuthorityStatus({
  title,
  evaluation,
}: {
  title: string;
  evaluation: EvidenceAuthorityEvaluation | null;
}) {
  return (
    <details>
      <summary>{title}</summary>
      {evaluation ? (
        <div className="assessment-governance-detail">
          <strong>{evaluation.readiness} · {evaluation.claim_results.length} claim(s)</strong>
          <span>Evaluated at the authority decision time: {new Date(evaluation.evaluated_at).toLocaleString()}</span>
          {evaluation.issues.length ? (
            <ul>{evaluation.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul>
          ) : <span>Every cited claim was approved with exact source provenance by this time.</span>}
          <span>{evaluation.evaluation_version}</span>
        </div>
      ) : <p className="form-help">No current authority exists to evaluate.</p>}
    </details>
  );
}

export function AssessmentGovernanceClient({ athleteId }: { athleteId?: string }) {
  const [projection, setProjection] = useState<AssessmentGovernanceProjection | null>(null);
  const [candidates, setCandidates] = useState<AssessmentGovernanceCandidateProjection | null>(null);
  const [loading, setLoading] = useState(true);
  const [ratifying, setRatifying] = useState<string | null>(null);
  const [attestations, setAttestations] = useState<Record<string, boolean>>({});
  const [message, setMessage] = useState("");
  const [messageKind, setMessageKind] = useState<"error" | "success">("error");

  const refresh = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      const [nextProjection, nextCandidates] = await Promise.all([
        fetchAssessmentGovernance(apiBaseUrl),
        fetchAssessmentGovernanceCandidates(apiBaseUrl),
      ]);
      setProjection(nextProjection);
      setCandidates(nextCandidates);
    } catch (error) {
      setMessageKind("error");
      setMessage(error instanceof Error ? error.message : "Unable to load assessment governance.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([
      fetchAssessmentGovernance(apiBaseUrl),
      fetchAssessmentGovernanceCandidates(apiBaseUrl),
    ])
      .then(([governanceResult, candidateResult]) => {
        if (active) {
          setProjection(governanceResult);
          setCandidates(candidateResult);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setMessageKind("error");
          setMessage(
            error instanceof Error ? error.message : "Unable to load assessment governance.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function ratify(candidateId: string) {
    const item = candidates?.items.find((entry) => entry.candidate.candidate_id === candidateId);
    if (!item || !attestations[candidateId] || item.status !== "available") return;
    setRatifying(candidateId);
    setMessage("");
    try {
      await ratifyAssessmentGovernanceCandidate(apiBaseUrl, item.candidate);
      const [nextProjection, nextCandidates] = await Promise.all([
        fetchAssessmentGovernance(apiBaseUrl),
        fetchAssessmentGovernanceCandidates(apiBaseUrl),
      ]);
      setProjection(nextProjection);
      setCandidates(nextCandidates);
      setAttestations((current) => ({ ...current, [candidateId]: false }));
      setMessageKind("success");
      setMessage(
        "The exact candidate was ratified and its evidence, protocol, policy, and decision history were saved atomically.",
      );
    } catch (error) {
      setMessageKind("error");
      setMessage(error instanceof Error ? error.message : "Unable to ratify the candidate.");
    } finally {
      setRatifying(null);
    }
  }

  const readyCount = projection?.items.filter((item) => item.readiness === "ready").length ?? 0;
  const blockedCount = projection?.items.filter((item) => item.readiness === "blocked").length ?? 0;
  const unreviewedCount = projection?.items.filter((item) => item.status === "unreviewed").length ?? 0;

  return (
    <main className="review-shell">
      <header className="review-topbar">
        <div>
          <p className="eyebrow">AGAS · Scientific governance</p>
          <h1>Assessment governance</h1>
          <p>
            Inspect protocol, measurement, evidence, and capability-estimation lineage before an
            assessment can participate in the athlete workflow.
          </p>
        </div>
        <nav className="review-route-links" aria-label="Reviewer routes">
          <Link href="/review/evidence" className="text-link">Evidence governance</Link>
          <Link href={athleteReviewHref("/review/planning-authorities", athleteId)} className="text-link">Planning authorities</Link>
          <Link href={athleteReviewHref("/review/queue", athleteId)} className="text-link">Planning queue</Link>
          <Link href={athleteHomeHref(athleteId)} className="text-link">Athlete PWA</Link>
        </nav>
      </header>

      {athleteId ? (
        <aside className="review-return" aria-label="Return to athlete setup">
          <div>
            <strong>This review is part of one athlete’s first-session path.</strong>
            <span>
              Review and approve only the exact release you accept. Then return to the assessment
              panel; the app will reopen the same athlete automatically.
            </span>
          </div>
          <Link className="secondary-button" href={athleteHomeHref(athleteId, "assessment-title")}>
            Return to assessment
          </Link>
        </aside>
      ) : null}

      <aside className="review-boundary" aria-label="Assessment-review authority boundary">
        <strong>Access is not scientific qualification.</strong>
        <span>
          This workbench can ratify only an exact prepared release after you review it below. It
          cannot edit scientific content or authorize an athlete to perform a test; athlete-specific
          eligibility remains a separate decision.
        </span>
      </aside>

      <section className="planning-queue-summary" aria-labelledby="candidate-title">
        <header>
          <div>
            <p className="eyebrow">Prepared by engineering and evidence review</p>
            <h2 id="candidate-title">Assessment candidates</h2>
          </div>
        </header>
        <p>
          These are complete, immutable proposals. Your role is to decide whether the exact narrow
          meaning and limitations are acceptable for the owner-only alpha—not to write the science.
        </p>
      </section>

      {candidates?.items.map((item) => {
        const candidate = item.candidate;
        const busy = ratifying === candidate.candidate_id;
        return (
          <section
            className="assessment-candidate"
            aria-labelledby={`candidate-${candidate.candidate_id}`}
            key={candidate.candidate_id}
          >
            <header>
              <div>
                <p className="eyebrow">{label(candidate.capability_domain)} · prepared candidate</p>
                <h2 id={`candidate-${candidate.candidate_id}`}>{candidate.release_label}</h2>
              </div>
              <span className={`status-badge status-badge--${item.status}`}>
                {item.status}
              </span>
            </header>
            <p>{candidate.summary}</p>

            <div className="assessment-candidate-meaning">
              <section>
                <h3>What it measures</h3>
                <p>{candidate.measures}</p>
              </section>
              <section>
                <h3>What it does not measure</h3>
                <ul>{candidate.does_not_measure.map((value) => <li key={value}>{value}</li>)}</ul>
              </section>
            </div>

            <details open>
              <summary>Required setup</summary>
              <ol>{candidate.setup_requirements.map((value) => <li key={value}>{value}</li>)}</ol>
            </details>
            <details open>
              <summary>Exact athlete protocol</summary>
              <ol>{candidate.protocol_steps.map((value) => <li key={value}>{value}</li>)}</ol>
            </details>
            <details open>
              <summary>Do not start or stop</summary>
              <ul>{candidate.stop_conditions.map((value) => <li key={value}>{value}</li>)}</ul>
            </details>
            <details>
              <summary>Product choices and interpretation</summary>
              <ul>{candidate.operational_choices.map((value) => <li key={value}>{value}</li>)}</ul>
              <p className="form-help">Stored scope: {candidate.estimate_scope}</p>
            </details>
            <details open>
              <summary>Important unresolved limitations</summary>
              <ul>{candidate.unresolved_limitations.map((value) => <li key={value}>{value}</li>)}</ul>
            </details>
            <details>
              <summary>{candidate.evidence.length} primary evidence source(s)</summary>
              <div className="assessment-candidate-evidence">
                {candidate.evidence.map((evidence) => (
                  <article key={evidence.source_url}>
                    <h3>{evidence.title}</h3>
                    <p><strong>Population:</strong> {evidence.population}</p>
                    <p><strong>Finding:</strong> {evidence.finding}</p>
                    <ul>{evidence.limitations.map((value) => <li key={value}>{value}</li>)}</ul>
                    <p><strong>Conflicts:</strong> {evidence.conflict_disclosure}</p>
                    <a href={evidence.source_url} target="_blank" rel="noreferrer" className="text-link">
                      Open primary PubMed record
                    </a>
                  </article>
                ))}
              </div>
            </details>

            <div className="assessment-candidate-integrity">
              <span>Prepared {new Date(candidate.prepared_at).toLocaleString()}</span>
              <code>{candidate.candidate_version}</code>
              <code>{candidate.content_digest}</code>
            </div>

            {item.issues.length ? (
              <p className="form-error" role="alert">{item.issues.join(" ")}</p>
            ) : null}
            {item.status === "ratified" ? (
              <p className="form-success">
                Ratified {item.ratified_at ? new Date(item.ratified_at).toLocaleString() : "previously"}.
                The protocol is now eligible for the separate athlete-screening workflow.
              </p>
            ) : item.status === "available" ? (
              <div className="assessment-candidate-approval">
                <label>
                  <input
                    type="checkbox"
                    checked={attestations[candidate.candidate_id] ?? false}
                    onChange={(event) => setAttestations((current) => ({
                      ...current,
                      [candidate.candidate_id]: event.target.checked,
                    }))}
                  />
                  <span>
                    I reviewed the measures, non-measures, protocol, evidence, conflicts, and
                    limitations above. I approve this exact release for the owner-only alpha.
                  </span>
                </label>
                <button
                  type="button"
                  className="primary-button"
                  disabled={!attestations[candidate.candidate_id] || busy}
                  onClick={() => void ratify(candidate.candidate_id)}
                >
                  {busy ? "Ratifying exact release…" : "Approve exact release"}
                </button>
                <p className="form-help">
                  This records your account and exact active reviewer-role assignment. It does not
                  claim that you are a clinician or independently qualified scientific reviewer.
                </p>
              </div>
            ) : null}
          </section>
        );
      })}
      {!candidates && loading ? <p className="planning-queue-empty">Loading prepared candidates…</p> : null}

      <section className="planning-queue-summary" aria-labelledby="assessment-summary-title">
        <header>
          <div>
            <p className="eyebrow">Derived governance state</p>
            <h2 id="assessment-summary-title">Assessment definitions</h2>
          </div>
          <button type="button" className="secondary-button" disabled={loading} onClick={() => void refresh()}>
            {loading ? "Refreshing…" : "Refresh governance"}
          </button>
        </header>
        <dl className="review-metadata">
          <div><dt>Operational chain</dt><dd>{readyCount}</dd></div>
          <div><dt>Blocked</dt><dd>{blockedCount}</dd></div>
          <div><dt>Unreviewed</dt><dd>{unreviewedCount}</dd></div>
        </dl>
      </section>

      {message ? (
        <div className="review-message">
          <p
            className={messageKind === "success" ? "form-success" : "form-error"}
            role={messageKind === "error" ? "alert" : "status"}
          >
            {message}
          </p>
          {messageKind === "success" && athleteId ? (
            <Link className="primary-button" href={athleteHomeHref(athleteId, "assessment-title")}>
              Continue this athlete’s assessment
            </Link>
          ) : null}
        </div>
      ) : null}
      {!projection && loading ? <p className="planning-queue-empty">Loading assessment governance…</p> : null}
      {projection && !projection.items.length ? (
        <p className="planning-queue-empty">
          No assessment definitions exist. Definitions and their scientific reviews must be loaded
          through governed local data operations; this screen does not seed them.
        </p>
      ) : null}
      {projection?.items.length ? (
        <section className="planning-queue-items assessment-governance-items" aria-label="Assessment governance items">
          {projection.items.map((item) => (
            <article key={item.definition.id}>
              <header>
                <div>
                  <p className="eyebrow">{label(item.definition.domain)}</p>
                  <h2>{item.definition.name}</h2>
                </div>
                <span className={`status-badge status-badge--${item.readiness}`}>
                  {item.readiness}
                </span>
              </header>
              <p>{item.definition.protocol_version} · {label(item.definition.intensity)} · {item.definition.unit_or_scale}</p>
              <dl>
                <div><dt>Protocol status</dt><dd>{label(item.status)}</dd></div>
                <div><dt>Observation</dt><dd>{label(item.definition.observation_type)}</dd></div>
              </dl>
              {item.issues.length ? (
                <section className="planning-queue-blockers">
                  <strong>{item.issues.length} governance issue(s)</strong>
                  <ul>{item.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul>
                </section>
              ) : <p className="form-help">The protocol-to-estimate governance chain is operational.</p>}

              <details open>
                <summary>Current protocol review</summary>
                {item.current_review ? (
                  <div className="assessment-governance-detail">
                    <strong>Sequence {item.current_review.sequence_number} · {label(item.current_review.decision)}</strong>
                    <span>{item.current_review.reviewer} · {item.current_review.review_version}</span>
                    <span>{item.current_review.measurement_schema
                      ? `${item.current_review.measurement_schema.label} · ${item.current_review.measurement_schema.measurement_schema_version}`
                      : "No reviewed measurement schema"}</span>
                    <span>{item.current_review.self_administered ? "Self-administration reviewed" : "Not approved for self-administration"}</span>
                    <span>{item.current_review.applicability_notes}</span>
                    <span><strong>Uncertainty:</strong> {item.current_review.uncertainty}</span>
                  </div>
                ) : <p className="form-help">No protocol review exists.</p>}
              </details>

              <details open>
                <summary>Current estimation policy</summary>
                {item.current_estimation_policy ? (
                  <div className="assessment-governance-detail">
                    <strong>Sequence {item.current_estimation_policy.sequence_number} · {label(item.current_estimation_policy.decision)}</strong>
                    <span>{item.current_estimation_policy.calculation_method} · valid {item.current_estimation_policy.valid_for_days} days</span>
                    <span>{item.current_estimation_policy.reviewed_by} · {item.current_estimation_policy.rule_version}</span>
                    <code>{item.current_estimation_policy.assessment_definition_review_id}</code>
                    <span><strong>Uncertainty:</strong> {item.current_estimation_policy.uncertainty}</span>
                  </div>
                ) : <p className="form-help">No capability-estimation policy exists.</p>}
              </details>

              <details>
                <summary>{item.review_history.length} protocol review(s), {item.estimation_policy_history.length} estimation policy record(s)</summary>
                <p className="form-help">Historical records remain visible and are never overwritten by a newer review.</p>
              </details>
              <details>
                <summary>{item.evidence_claims.length} referenced evidence claim(s)</summary>
                {item.evidence_claims.map((claim) => (
                  <div className="assessment-governance-detail" key={claim.id}>
                    <strong>{claim.claim}</strong>
                    <span>{claim.population} · {claim.study_design}</span>
                    <span>Strength {label(claim.evidence_strength)} · applicability {label(claim.athlete_applicability)}</span>
                    <span>{claim.applicability_notes}</span>
                    <span><strong>Uncertainty:</strong> {claim.uncertainty}</span>
                    <code>{claim.source_identifiers.map((source) => `${source.scheme}:${source.value}`).join(" · ")}</code>
                  </div>
                ))}
              </details>
              <EvidenceAuthorityStatus
                title="Protocol-review evidence readiness"
                evaluation={item.review_evidence_governance}
              />
              <EvidenceAuthorityStatus
                title="Estimation-policy evidence readiness"
                evaluation={item.estimation_policy_evidence_governance}
              />
              <code>{item.definition.id}</code>
            </article>
          ))}
        </section>
      ) : null}
      {projection ? (
        <p className="form-help">Projected {new Date(projection.projected_at).toLocaleString()} · {projection.projection_version}</p>
      ) : null}
    </main>
  );
}
