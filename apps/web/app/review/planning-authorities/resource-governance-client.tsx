"use client";

import { useCallback, useEffect, useState } from "react";

import {
  fetchResourceGovernanceCandidates,
  ratifyResourceGovernanceCandidate,
  type ResourceGovernanceCandidateProjection,
} from "@/lib/resource-governance";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function ResourceGovernanceClient() {
  const [projection, setProjection] = useState<ResourceGovernanceCandidateProjection | null>(null);
  const [confirmed, setConfirmed] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    setBusy(true);
    setMessage("");
    try {
      setProjection(await fetchResourceGovernanceCandidates(apiBaseUrl));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load resource authorities.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    void fetchResourceGovernanceCandidates(apiBaseUrl)
      .then((result) => {
        if (active) setProjection(result);
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(error instanceof Error ? error.message : "Unable to load resource authorities.");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function ratify(candidateId: string) {
    const item = projection?.items.find((entry) => entry.candidate.candidate_id === candidateId);
    if (!item || item.status !== "available" || !confirmed[candidateId]) return;
    setBusy(true);
    setMessage("");
    try {
      await ratifyResourceGovernanceCandidate(apiBaseUrl, item.candidate);
      setProjection(await fetchResourceGovernanceCandidates(apiBaseUrl));
      setConfirmed((current) => ({ ...current, [candidateId]: false }));
      setMessage("The exact evidence, equipment, exercise, and policy bundle was saved atomically.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to approve resource authorities.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="planning-queue-summary" aria-labelledby="resource-authorities-title">
      <header>
        <div>
          <p className="eyebrow">Strategy-to-block prerequisites</p>
          <h2 id="resource-authorities-title">First-block authority candidates</h2>
        </div>
        <button type="button" className="secondary-button" disabled={busy} onClick={() => void refresh()}>
          {busy ? "Refreshing…" : "Refresh"}
        </button>
      </header>
      <p>
        Engineering prepared the narrow ontology and policies needed after the first strategy.
        Approval creates no dose, block, week, or workout.
      </p>

      {projection?.items.map((item) => {
        const candidate = item.candidate;
        return (
          <article className="assessment-candidate" key={candidate.candidate_id}>
            <header>
              <div>
                <p className="eyebrow">Exact resource bundle · owner alpha</p>
                <h3>{candidate.release_label}</h3>
              </div>
              <span className={`status-badge status-badge--${item.status}`}>{item.status}</span>
            </header>
            <p>{candidate.summary}</p>
            <details open>
              <summary>Exact artifacts</summary>
              <ul>{candidate.exact_artifacts.map((value) => <li key={value}>{value}</li>)}</ul>
            </details>
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
              <summary>Operational choices</summary>
              <ul>{candidate.operational_choices.map((value) => <li key={value}>{value}</li>)}</ul>
            </details>
            <details open>
              <summary>Limitations that remain</summary>
              <ul>{candidate.unresolved_limitations.map((value) => <li key={value}>{value}</li>)}</ul>
            </details>
            <details>
              <summary>Primary evidence</summary>
              {candidate.evidence.map((evidence) => (
                <section key={evidence.source_url}>
                  <h3>{evidence.title}</h3>
                  <p><strong>Population:</strong> {evidence.population}</p>
                  <p><strong>Finding:</strong> {evidence.finding}</p>
                  <ul>{evidence.limitations.map((value) => <li key={value}>{value}</li>)}</ul>
                  <a className="text-link" href={evidence.source_url} target="_blank" rel="noreferrer">
                    Open primary full text
                  </a>
                </section>
              ))}
            </details>
            <div className="assessment-candidate-integrity">
              <code>{candidate.candidate_version}</code>
              <code>{candidate.content_digest}</code>
            </div>
            {item.issues.length ? <p className="form-error">{item.issues.join(" ")}</p> : null}
            {item.status === "available" ? (
              <div className="assessment-candidate-approval">
                <label>
                  <input
                    type="checkbox"
                    checked={confirmed[candidate.candidate_id] ?? false}
                    onChange={(event) => setConfirmed((current) => ({
                      ...current,
                      [candidate.candidate_id]: event.target.checked,
                    }))}
                  />
                  <span>
                    I reviewed the exact artifacts, evidence scope, engineering choices, and
                    limitations for this owner-only alpha.
                  </span>
                </label>
                <button
                  type="button"
                  className="primary-button"
                  disabled={!confirmed[candidate.candidate_id] || busy}
                  onClick={() => void ratify(candidate.candidate_id)}
                >
                  {busy ? "Saving exact bundle…" : "Approve resource authorities"}
                </button>
              </div>
            ) : item.status === "ratified" ? (
              <p className="form-success">
                Ratified {item.ratified_at ? new Date(item.ratified_at).toLocaleString() : "previously"}.
                The exact artifacts can now support a prepared resource demand.
              </p>
            ) : null}
          </article>
        );
      })}
      {message ? <p className={message.startsWith("The exact") ? "form-success" : "form-error"} role="status">{message}</p> : null}
    </section>
  );
}
