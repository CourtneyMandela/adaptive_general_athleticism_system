"use client";

import { useCallback, useEffect, useState } from "react";

import {
  fetchCompetencyFloorCandidates,
  ratifyCompetencyFloorCandidateBatch,
  ratifyCompetencyFloorCandidate,
  type CompetencyFloorCandidateProjection,
} from "@/lib/competency-floor-governance";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function CompetencyFloorGovernanceClient() {
  const [projection, setProjection] = useState<CompetencyFloorCandidateProjection | null>(null);
  const [loading, setLoading] = useState(true);
  const [ratifying, setRatifying] = useState<string | null>(null);
  const [attestations, setAttestations] = useState<Record<string, boolean>>({});
  const [batchAttestation, setBatchAttestation] = useState(false);
  const [message, setMessage] = useState("");
  const [messageKind, setMessageKind] = useState<"error" | "success">("error");

  const refresh = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      setProjection(await fetchCompetencyFloorCandidates(apiBaseUrl));
    } catch (error) {
      setMessageKind("error");
      setMessage(error instanceof Error ? error.message : "Unable to load competency floors.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    void fetchCompetencyFloorCandidates(apiBaseUrl)
      .then((result) => {
        if (active) setProjection(result);
      })
      .catch((error: unknown) => {
        if (active) {
          setMessageKind("error");
          setMessage(error instanceof Error ? error.message : "Unable to load competency floors.");
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
      await ratifyCompetencyFloorCandidate(apiBaseUrl, item.candidate);
      setProjection(await fetchCompetencyFloorCandidates(apiBaseUrl));
      setAttestations((current) => ({ ...current, [candidateId]: false }));
      setMessageKind("success");
      setMessage(
        "The source, extracted claim, evidence review, age-bounded floor, approval, and decision history were saved atomically.",
      );
    } catch (error) {
      setMessageKind("error");
      setMessage(error instanceof Error ? error.message : "Unable to ratify the candidate.");
    } finally {
      setRatifying(null);
    }
  }

  async function ratifyBatch() {
    if (!projection || !batchAttestation) return;
    setRatifying("batch");
    setMessage("");
    try {
      await ratifyCompetencyFloorCandidateBatch(apiBaseUrl, projection.batch);
      setProjection(await fetchCompetencyFloorCandidates(apiBaseUrl));
      setBatchAttestation(false);
      setAttestations({});
      setMessageKind("success");
      setMessage(
        "The exact batch and every artifact-specific evidence, floor, review, and decision record were saved in one transaction.",
      );
    } catch (error) {
      setMessageKind("error");
      setMessage(error instanceof Error ? error.message : "Unable to ratify the candidate batch.");
    } finally {
      setRatifying(null);
    }
  }

  const availableCount = projection?.items.filter((item) => item.status === "available").length ?? 0;
  const batchBlocked = projection?.items.some((item) => item.status === "conflict") ?? false;

  return (
    <>
      <section className="planning-queue-summary" aria-labelledby="floor-candidate-title">
        <header>
          <div>
            <p className="eyebrow">Prepared by engineering and evidence review</p>
            <h2 id="floor-candidate-title">Competency-floor candidates</h2>
          </div>
          <button type="button" className="secondary-button" onClick={() => void refresh()}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </header>
        <p>
          A floor is a narrow comparison point for a matching estimate. It is not a medical cutoff,
          ideal target, or permission to train.
        </p>
        {projection && availableCount > 0 ? (
          <div className="assessment-candidate-approval">
            <label>
              <input
                type="checkbox"
                checked={batchAttestation}
                onChange={(event) => setBatchAttestation(event.target.checked)}
              />
              <span>
                I reviewed all {projection.batch.candidates.length} exact candidates, including
                each threshold, population, evidence boundary, and limitation. I approve this
                content-addressed batch for the owner-only alpha.
              </span>
            </label>
            <div className="assessment-candidate-integrity">
              <code>{projection.batch.batch_version}</code>
              <code>{projection.batch.content_digest}</code>
            </div>
            <button
              type="button"
              className="primary-button"
              disabled={!batchAttestation || batchBlocked || ratifying !== null}
              onClick={() => void ratifyBatch()}
            >
              {ratifying === "batch" ? "Ratifying exact batch…" : `Approve exact batch (${availableCount} new)`}
            </button>
            {batchBlocked ? (
              <p className="form-error">Resolve the conflicting artifact before batch approval.</p>
            ) : null}
          </div>
        ) : null}
      </section>

      {projection?.items.map((item) => {
        const candidate = item.candidate;
        const busy = ratifying === candidate.candidate_id;
        return (
          <section
            className="assessment-candidate"
            aria-labelledby={`floor-candidate-${candidate.candidate_id}`}
            key={candidate.candidate_id}
          >
            <header>
              <div>
                <p className="eyebrow">Age-bounded lower reference · owner alpha</p>
                <h2 id={`floor-candidate-${candidate.candidate_id}`}>
                  {candidate.release_label}
                </h2>
              </div>
              <span className={`status-badge status-badge--${item.status}`}>{item.status}</span>
            </header>
            <p>{candidate.summary}</p>

            <div className="assessment-candidate-meaning">
              <section>
                <h3>Where the number came from</h3>
                <p><strong>{candidate.authority_basis.numeric_value_origin.replaceAll("_", " ")}</strong></p>
                <p>{candidate.authority_basis.numeric_value_explanation}</p>
              </section>
              <section>
                <h3>Why AGAS may use it</h3>
                <p><strong>{candidate.authority_basis.operational_use_origin.replaceAll("_", " ")}</strong></p>
                <p>{candidate.authority_basis.operational_use_explanation}</p>
              </section>
            </div>

            <div className="assessment-candidate-meaning">
              <section>
                <h3>Exact comparison</h3>
                <p>
                  <strong>{candidate.threshold} {candidate.unit_or_scale}</strong>, higher is better,
                  ages {candidate.minimum_age_years}-{candidate.maximum_age_years} only.
                </p>
                <p><strong>Scope:</strong> {candidate.estimate_scope}</p>
              </section>
              <section>
                <h3>What it does not establish</h3>
                <ul>{candidate.does_not_establish.map((value) => <li key={value}>{value}</li>)}</ul>
              </section>
            </div>

            <details open>
              <summary>What this floor governs</summary>
              <ul>{candidate.governs.map((value) => <li key={value}>{value}</li>)}</ul>
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
                      Open primary full-text record
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
                The floor can now be applied only to an age-compatible matching estimate.
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
                    I reviewed the population, exact threshold, scope, and limitations. I approve
                    this exact provisional floor for the owner-only alpha.
                  </span>
                </label>
                <button
                  type="button"
                  className="primary-button"
                  disabled={!attestations[candidate.candidate_id] || ratifying !== null}
                  onClick={() => void ratify(candidate.candidate_id)}
                >
                  {busy ? "Ratifying exact floor…" : "Approve exact floor"}
                </button>
              </div>
            ) : null}
          </section>
        );
      })}

      {!projection && loading ? <p className="planning-queue-empty">Loading prepared floor…</p> : null}
      {message ? (
        <p className={messageKind === "success" ? "form-success" : "form-error"} role="status">
          {message}
        </p>
      ) : null}
    </>
  );
}
