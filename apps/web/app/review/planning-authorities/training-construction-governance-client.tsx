"use client";

import { useCallback, useEffect, useState } from "react";

import {
  fetchTrainingConstructionCandidates,
  ratifyTrainingConstructionCandidate,
  type TrainingConstructionCandidateProjection,
} from "@/lib/training-construction-governance";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function TrainingConstructionGovernanceClient() {
  const [projection, setProjection] = useState<TrainingConstructionCandidateProjection | null>(null);
  const [confirmed, setConfirmed] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    setBusy(true);
    setMessage("");
    try {
      setProjection(await fetchTrainingConstructionCandidates(apiBaseUrl));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load construction authorities.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    void fetchTrainingConstructionCandidates(apiBaseUrl)
      .then((result) => {
        if (active) setProjection(result);
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(error instanceof Error ? error.message : "Unable to load construction authorities.");
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
      await ratifyTrainingConstructionCandidate(apiBaseUrl, item.candidate);
      setProjection(await fetchTrainingConstructionCandidates(apiBaseUrl));
      setConfirmed((current) => ({ ...current, [candidateId]: false }));
      setMessage("The exact dose, scheduling, progression, and readiness authorities were saved atomically.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to approve construction authorities.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="planning-queue-summary" aria-labelledby="construction-authorities-title">
      <header>
        <div>
          <p className="eyebrow">First-session prerequisites · batched review</p>
          <h2 id="construction-authorities-title">Training-construction authorities</h2>
        </div>
        <button type="button" className="secondary-button" disabled={busy} onClick={() => void refresh()}>
          {busy ? "Refreshing…" : "Refresh"}
        </button>
      </header>
      <p>
        Engineering prepared the exact rules needed to turn a current estimate into a bounded first
        session. One approval covers the complete, digest-locked batch; it does not schedule a workout.
      </p>

      {projection?.items.map((item) => {
        const candidate = item.candidate;
        return (
          <article className="assessment-candidate" key={candidate.candidate_id}>
            <header>
              <div>
                <p className="eyebrow">Exact four-authority bundle · owner alpha</p>
                <h3>{candidate.release_label}</h3>
              </div>
              <span className={`status-badge status-badge--${item.status}`}>{item.status}</span>
            </header>
            <p>{candidate.summary}</p>
            <aside className="review-boundary">
              <strong>Evidence direction and engineering numbers stay separate.</strong>
              <span>{candidate.authority_basis.scientific_support}</span>
              <span>{candidate.authority_basis.engineering_prior}</span>
            </aside>
            <details open>
              <summary>Exact artifacts in this batch</summary>
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
              <summary>Limitations that remain</summary>
              <ul>{candidate.unresolved_limitations.map((value) => <li key={value}>{value}</li>)}</ul>
            </details>
            <details>
              <summary>Evidence boundary</summary>
              {candidate.evidence.map((evidence) => (
                <section key={evidence.claim_id}>
                  <h3>{evidence.title}</h3>
                  <p><strong>Supports:</strong> {evidence.supported_use}</p>
                  <p><strong>Does not support:</strong> {evidence.unsupported_specifics}</p>
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
                    I reviewed the full digest-locked batch, including which values are provisional
                    engineering choices rather than scientific findings.
                  </span>
                </label>
                <button
                  type="button"
                  className="primary-button"
                  disabled={!confirmed[candidate.candidate_id] || busy}
                  onClick={() => void ratify(candidate.candidate_id)}
                >
                  {busy ? "Saving exact batch…" : "Approve construction batch"}
                </button>
              </div>
            ) : item.status === "ratified" ? (
              <p className="form-success">
                Ratified {item.ratified_at ? new Date(item.ratified_at).toLocaleString() : "previously"}.
                These authorities can now support athlete-specific first-session preparation.
              </p>
            ) : null}
          </article>
        );
      })}
      {message ? <p className={message.startsWith("The exact") ? "form-success" : "form-error"} role="status">{message}</p> : null}
    </section>
  );
}
