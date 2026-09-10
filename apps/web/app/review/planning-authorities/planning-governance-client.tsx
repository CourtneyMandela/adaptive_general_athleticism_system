"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  fetchPlanningGovernanceCandidates,
  ratifyPlanningGovernanceCandidate,
  type PlanningGovernanceCandidateProjection,
} from "@/lib/planning-governance";

import { CompetencyFloorGovernanceClient } from "./competency-floor-governance-client";
import { ResourceGovernanceClient } from "./resource-governance-client";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function PlanningGovernanceClient() {
  const [projection, setProjection] = useState<PlanningGovernanceCandidateProjection | null>(null);
  const [loading, setLoading] = useState(true);
  const [ratifying, setRatifying] = useState<string | null>(null);
  const [attestations, setAttestations] = useState<Record<string, boolean>>({});
  const [message, setMessage] = useState("");
  const [messageKind, setMessageKind] = useState<"error" | "success">("error");

  const refresh = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      setProjection(await fetchPlanningGovernanceCandidates(apiBaseUrl));
    } catch (error) {
      setMessageKind("error");
      setMessage(error instanceof Error ? error.message : "Unable to load planning governance.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    void fetchPlanningGovernanceCandidates(apiBaseUrl)
      .then((result) => {
        if (active) setProjection(result);
      })
      .catch((error: unknown) => {
        if (active) {
          setMessageKind("error");
          setMessage(error instanceof Error ? error.message : "Unable to load planning governance.");
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
    const item = projection?.items.find((entry) => entry.candidate.candidate_id === candidateId);
    if (!item || item.status !== "available" || !attestations[candidateId]) return;
    setRatifying(candidateId);
    setMessage("");
    try {
      await ratifyPlanningGovernanceCandidate(apiBaseUrl, item.candidate);
      setProjection(await fetchPlanningGovernanceCandidates(apiBaseUrl));
      setAttestations((current) => ({ ...current, [candidateId]: false }));
      setMessageKind("success");
      setMessage(
        "The exact policy, evidence review, approval, and decision history were saved atomically.",
      );
    } catch (error) {
      setMessageKind("error");
      setMessage(error instanceof Error ? error.message : "Unable to ratify the candidate.");
    } finally {
      setRatifying(null);
    }
  }

  return (
    <main className="review-shell">
      <header className="review-topbar">
        <div>
          <p className="eyebrow">AGAS · Planning governance</p>
          <h1>Prepared planning authorities</h1>
          <p>
            Review the engineering and evidence work behind a versioned planning policy. You are
            approving exact prepared content, not being asked to invent the algorithm.
          </p>
        </div>
        <nav className="review-route-links" aria-label="Reviewer routes">
          <Link href="/review/assessments" className="text-link">Assessment governance</Link>
          <Link href="/review" className="text-link">Initial planning</Link>
          <Link href="/review/queue" className="text-link">Planning queue</Link>
          <Link href="/" className="text-link">Athlete PWA</Link>
        </nav>
      </header>

      <aside className="review-boundary" aria-label="Planning-review authority boundary">
        <strong>Approval is narrow and reversible through versioning.</strong>
        <span>
          Ratification permits this exact policy to rank later reviewed inputs. It does not decide
          your priority, create a workout, authorize unsafe training, or prove its numeric weights
          are scientifically optimal.
        </span>
      </aside>

      <section className="planning-queue-summary" aria-labelledby="candidate-title">
        <header>
          <div>
            <p className="eyebrow">Prepared by engineering and evidence review</p>
            <h2 id="candidate-title">Priority-policy candidates</h2>
          </div>
          <button type="button" className="secondary-button" onClick={() => void refresh()}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </header>
        <p>
          The first candidate is deliberately conservative and transparent. It removes hidden
          defaults and the prior requirement for you to author numeric policy JSON.
        </p>
      </section>

      {projection?.items.map((item) => {
        const candidate = item.candidate;
        const busy = ratifying === candidate.candidate_id;
        return (
          <section
            className="assessment-candidate"
            aria-labelledby={`planning-candidate-${candidate.candidate_id}`}
            key={candidate.candidate_id}
          >
            <header>
              <div>
                <p className="eyebrow">Versioned ranking policy · owner alpha</p>
                <h2 id={`planning-candidate-${candidate.candidate_id}`}>
                  {candidate.release_label}
                </h2>
              </div>
              <span className={`status-badge status-badge--${item.status}`}>{item.status}</span>
            </header>
            <p>{candidate.summary}</p>

            <div className="assessment-candidate-meaning">
              <section>
                <h3>What it governs</h3>
                <ul>{candidate.governs.map((value) => <li key={value}>{value}</li>)}</ul>
              </section>
              <section>
                <h3>What it does not establish</h3>
                <ul>{candidate.does_not_establish.map((value) => <li key={value}>{value}</li>)}</ul>
              </section>
            </div>

            <details open>
              <summary>Exact operational choices</summary>
              <ul>{candidate.operational_choices.map((value) => <li key={value}>{value}</li>)}</ul>
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

            {item.issues.length ? <p className="form-error" role="alert">{item.issues.join(" ")}</p> : null}
            {item.status === "ratified" ? (
              <p className="form-success">
                Ratified {item.ratified_at ? new Date(item.ratified_at).toLocaleString() : "previously"}.
                This policy can now appear in initial-planning preparation.
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
                    I reviewed the policy scope, operational choices, evidence, and limitations. I
                    approve this exact release for the owner-only alpha.
                  </span>
                </label>
                <button
                  type="button"
                  className="primary-button"
                  disabled={!attestations[candidate.candidate_id] || busy}
                  onClick={() => void ratify(candidate.candidate_id)}
                >
                  {busy ? "Ratifying exact policy…" : "Approve exact policy"}
                </button>
              </div>
            ) : null}
          </section>
        );
      })}

      {!projection && loading ? <p className="planning-queue-empty">Loading prepared policy…</p> : null}
      {message ? (
        <p className={messageKind === "success" ? "form-success" : "form-error"} role="status">
          {message}
        </p>
      ) : null}
      <CompetencyFloorGovernanceClient />
      <ResourceGovernanceClient />
    </main>
  );
}
