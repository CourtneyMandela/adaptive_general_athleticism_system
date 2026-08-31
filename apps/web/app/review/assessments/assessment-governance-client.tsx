"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  fetchAssessmentGovernance,
  type AssessmentGovernanceProjection,
} from "@/lib/assessment-governance";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function label(value: string): string {
  return value.replaceAll("_", " ");
}

export function AssessmentGovernanceClient() {
  const [projection, setProjection] = useState<AssessmentGovernanceProjection | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      setProjection(await fetchAssessmentGovernance(apiBaseUrl));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load assessment governance.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    fetchAssessmentGovernance(apiBaseUrl)
      .then((result) => {
        if (active) setProjection(result);
      })
      .catch((error: unknown) => {
        if (active) {
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
          <Link href="/review/queue" className="text-link">Planning queue</Link>
          <Link href="/" className="text-link">Athlete PWA</Link>
        </nav>
      </header>

      <aside className="review-boundary" aria-label="Assessment-review authority boundary">
        <strong>Access is not scientific qualification.</strong>
        <span>
          This workbench is read-only. It exposes immutable review history and missing governance;
          it cannot approve a protocol, invent evidence, or authorize an athlete to perform a test.
        </span>
      </aside>

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

      {message ? <p className="form-error review-message" role="alert">{message}</p> : null}
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
