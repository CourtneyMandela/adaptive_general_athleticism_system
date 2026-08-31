"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  fetchEvidenceGovernance,
  type EvidenceGovernanceProjection,
} from "@/lib/evidence-governance";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function label(value: string): string {
  return value.replaceAll("_", " ");
}

export function EvidenceGovernanceClient() {
  const [projection, setProjection] = useState<EvidenceGovernanceProjection | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      setProjection(await fetchEvidenceGovernance(apiBaseUrl));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load evidence governance.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    fetchEvidenceGovernance(apiBaseUrl)
      .then((result) => {
        if (active) setProjection(result);
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(error instanceof Error ? error.message : "Unable to load evidence governance.");
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
          <h1>Evidence governance</h1>
          <p>Trace each training claim to exact source snapshots and immutable review history.</p>
        </div>
        <nav className="review-route-links" aria-label="Reviewer routes">
          <Link href="/review/assessments" className="text-link">Assessment governance</Link>
          <Link href="/review/queue" className="text-link">Planning queue</Link>
          <Link href="/" className="text-link">Athlete PWA</Link>
        </nav>
      </header>

      <aside className="review-boundary" aria-label="Evidence-review authority boundary">
        <strong>Access is not scientific qualification.</strong>
        <span>
          This workbench is read-only. It cannot approve a claim, fabricate a source, or turn an
          imported summary into operational evidence.
        </span>
      </aside>

      <section className="planning-queue-summary" aria-labelledby="evidence-summary-title">
        <header>
          <div><p className="eyebrow">Derived governance state</p><h2 id="evidence-summary-title">Evidence claims</h2></div>
          <button type="button" className="secondary-button" disabled={loading} onClick={() => void refresh()}>
            {loading ? "Refreshing…" : "Refresh governance"}
          </button>
        </header>
        <dl className="review-metadata">
          <div><dt>Ready</dt><dd>{readyCount}</dd></div>
          <div><dt>Blocked</dt><dd>{blockedCount}</dd></div>
          <div><dt>Unreviewed</dt><dd>{unreviewedCount}</dd></div>
        </dl>
      </section>

      {message ? <p className="form-error review-message" role="alert">{message}</p> : null}
      {!projection && loading ? <p className="planning-queue-empty">Loading evidence governance…</p> : null}
      {projection && !projection.items.length ? (
        <p className="planning-queue-empty">No evidence claims exist. This screen does not seed or invent them.</p>
      ) : null}
      {projection?.items.length ? (
        <section className="planning-queue-items assessment-governance-items" aria-label="Evidence governance items">
          {projection.items.map((item) => (
            <article key={item.claim.id}>
              <header>
                <div><p className="eyebrow">{label(item.claim.domain)}</p><h2>{item.claim.claim}</h2></div>
                <span className={`status-badge status-badge--${item.readiness}`}>{item.readiness}</span>
              </header>
              <p>{item.claim.population} · {item.claim.study_design}</p>
              <dl>
                <div><dt>Review status</dt><dd>{label(item.status)}</dd></div>
                <div><dt>Strength</dt><dd>{label(item.claim.evidence_strength)}</dd></div>
                <div><dt>Applicability</dt><dd>{label(item.claim.athlete_applicability)}</dd></div>
                <div><dt>Claim version</dt><dd>{item.claim.claim_version}</dd></div>
              </dl>
              {item.issues.length ? (
                <section className="planning-queue-blockers">
                  <strong>{item.issues.length} governance issue(s)</strong>
                  <ul>{item.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul>
                </section>
              ) : <p className="form-help">The source-to-claim review chain is operational.</p>}

              <details open>
                <summary>Current scientific review</summary>
                {item.current_review ? (
                  <div className="assessment-governance-detail">
                    <strong>Sequence {item.current_review.sequence_number} · {label(item.current_review.decision)}</strong>
                    <span>{item.current_review.reviewer} · {item.current_review.review_version}</span>
                    <span><strong>Source verification:</strong> {item.current_review.source_verification_rationale}</span>
                    <span><strong>Extraction:</strong> {item.current_review.extraction_rationale}</span>
                    <span><strong>Strength:</strong> {item.current_review.evidence_strength_rationale}</span>
                    <span><strong>Applicability:</strong> {item.current_review.applicability_rationale}</span>
                    <span><strong>Uncertainty:</strong> {item.current_review.uncertainty}</span>
                    <span><strong>Conflict disclosure:</strong> {item.current_review.conflict_disclosure}</span>
                  </div>
                ) : <p className="form-help">No scientific review exists.</p>}
              </details>

              <details open>
                <summary>{item.sources.length} exact source snapshot(s)</summary>
                {item.sources.map((source) => (
                  <div className="assessment-governance-detail" key={source.id}>
                    <strong>{source.title}</strong>
                    <span>{source.authors.join(", ") || "Authors not present in snapshot"}</span>
                    <span>{source.journal ?? "Journal unavailable"} · {source.publication_year ?? "Year unavailable"}</span>
                    <span>{source.metadata_provider} · retrieved {new Date(source.retrieved_at).toLocaleString()}</span>
                    <code>{source.primary_identifier.scheme}:{source.primary_identifier.value}</code>
                  </div>
                ))}
              </details>
              <details><summary>{item.review_history.length} immutable review record(s)</summary></details>
              <p><strong>Applicability notes:</strong> {item.claim.applicability_notes}</p>
              <p><strong>Claim uncertainty:</strong> {item.claim.uncertainty}</p>
              <code>{item.claim.id}</code>
            </article>
          ))}
        </section>
      ) : null}
      {projection ? <p className="form-help">Projected {new Date(projection.projected_at).toLocaleString()} · {projection.projection_version}</p> : null}
    </main>
  );
}
