"use client";

import { useEffect, useState } from "react";

import {
  fetchCompetencyFloorProposals,
  type CompetencyFloorProposalBatch,
} from "@/lib/competency-floor-proposals";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function CompetencyFloorProposalClient() {
  const [batch, setBatch] = useState<CompetencyFloorProposalBatch | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    void fetchCompetencyFloorProposals(apiBaseUrl)
      .then((result) => {
        if (active) setBatch(result);
      })
      .catch((error: unknown) => {
        if (active) setMessage(error instanceof Error ? error.message : "Unable to load floor proposals.");
      });
    return () => {
      active = false;
    };
  }, []);

  const sourceById = new Map(batch?.source_catalog.map((source) => [source.source_id, source]));

  return (
    <>
      <section className="planning-queue-summary" aria-labelledby="floor-proposal-title">
        <header>
          <div>
            <p className="eyebrow">Research batch · review before governance</p>
            <h2 id="floor-proposal-title">Adult competency-floor proposals</h2>
          </div>
          <span className="status-badge status-badge--proposal_only">proposal only</span>
        </header>
        <p>
          These are the researched values to challenge, change, or reject. They cannot yet affect
          assessment selection, planning, or a workout. Textbook reference values and unsupported
          professional-judgment proposals are labeled separately.
        </p>
        {batch ? (
          <>
            <dl className="assessment-summary">
              <div><dt>Proposals</dt><dd>{batch.proposals.length}</dd></div>
              <div><dt>Capability domains</dt><dd>{new Set(batch.proposals.map((item) => item.domain)).size}</dd></div>
              <div><dt>Textbook sources</dt><dd>{batch.source_catalog.length}</dd></div>
              <div><dt>Active floors created</dt><dd>0</dd></div>
            </dl>
            <p className="form-help">{batch.release_boundary}</p>
            <div className="assessment-candidate-integrity">
              <code>{batch.batch_version}</code>
              <code>{batch.content_digest}</code>
            </div>
          </>
        ) : null}
        {message ? <p className="form-error" role="alert">{message}</p> : null}
        {!batch && !message ? <p className="planning-queue-empty">Loading researched proposals…</p> : null}
      </section>

      {batch?.proposals.map((proposal) => {
        const sources = proposal.source_ids.flatMap((sourceId) => {
          const source = sourceById.get(sourceId);
          return source ? [source] : [];
        });
        const direction = proposal.comparison_direction === "higher_is_better"
          ? "higher is better"
          : "lower is better";
        return (
          <section className="assessment-candidate" key={proposal.proposal_id}>
            <header>
              <div>
                <p className="eyebrow">{proposal.domain.replaceAll("_", " ")} · {proposal.sex_scope.replaceAll("_", " ")}</p>
                <h2>{proposal.label}</h2>
              </div>
              <span className={`status-badge status-badge--match-${proposal.population_match}`}>
                {proposal.population_match} population match
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
            <details open>
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
              <summary>Questions for owner review</summary>
              <ul>{proposal.review_questions.map((value) => <li key={value}>{value}</li>)}</ul>
            </details>
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
