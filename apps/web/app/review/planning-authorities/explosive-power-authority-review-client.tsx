"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchCompetencyFloorCandidates } from "@/lib/competency-floor-governance";
import {
  selectExplosivePowerAuthorityReview,
  type ExplosivePowerAuthorityReview,
} from "@/lib/explosive-power-authority-review";
import { fetchResourceGovernanceCandidates } from "@/lib/resource-governance";
import { fetchTrainingConstructionCandidates } from "@/lib/training-construction-governance";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function ExplosivePowerAuthorityReviewClient() {
  const [review, setReview] = useState<ExplosivePowerAuthorityReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      const [floors, resources, construction] = await Promise.all([
        fetchCompetencyFloorCandidates(apiBaseUrl),
        fetchResourceGovernanceCandidates(apiBaseUrl),
        fetchTrainingConstructionCandidates(apiBaseUrl),
      ]);
      setReview(selectExplosivePowerAuthorityReview(floors, resources, construction));
    } catch (error) {
      setReview(null);
      setMessage(
        error instanceof Error ? error.message : "Unable to load the explosive-power review.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    void Promise.all([
      fetchCompetencyFloorCandidates(apiBaseUrl),
      fetchResourceGovernanceCandidates(apiBaseUrl),
      fetchTrainingConstructionCandidates(apiBaseUrl),
    ])
      .then(([floors, resources, construction]) => {
        if (active) {
          setReview(selectExplosivePowerAuthorityReview(floors, resources, construction));
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(
            error instanceof Error ? error.message : "Unable to load the explosive-power review.",
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

  if (!review && !loading && !message) return null;

  const floor = review?.floor.candidate;
  const resource = review?.resource.candidate;
  const construction = review?.construction.candidate;

  return (
    <section className="planning-queue-summary explosive-power-review" aria-labelledby="explosive-power-review-title">
      <header>
        <div>
          <p className="eyebrow">Concise why · provisional explosive-power path</p>
          <h2 id="explosive-power-review-title">Why AGAS may propose jump training</h2>
        </div>
        <button type="button" className="secondary-button" disabled={loading} onClick={() => void refresh()}>
          {loading ? "Loading…" : "Refresh path"}
        </button>
      </header>

      {review && floor && resource && construction ? (
        <>
          <p>
            This view connects the exact comparison, evidence direction, feasible training means,
            and starting dose. It does not merge their approvals or turn any candidate into an
            athlete plan.
          </p>

          <div className="explosive-power-path" aria-label="Explosive-power authority path">
            <article>
              <div className="explosive-power-path__heading">
                <span>1</span>
                <div>
                  <p className="eyebrow">Identify a provisional need</p>
                  <h3>{floor.release_label}</h3>
                </div>
                <span className={`status-badge status-badge--${review.floor.status}`}>
                  {review.floor.status}
                </span>
              </div>
              <p className="explosive-power-path__value">
                {floor.threshold} {floor.unit_or_scale}
              </p>
              <p>{floor.authority_basis.numeric_value_explanation}</p>
              <a className="text-link" href={`#authority-${floor.slug}`}>Review exact floor</a>
            </article>

            <article>
              <div className="explosive-power-path__heading">
                <span>2</span>
                <div>
                  <p className="eyebrow">Choose an evidence-linked means</p>
                  <h3>{resource.release_label}</h3>
                </div>
                <span className={`status-badge status-badge--${review.resource.status}`}>
                  {review.resource.status}
                </span>
              </div>
              <p>{resource.summary}</p>
              {resource.governs[3] ? <p><strong>Envelope:</strong> {resource.governs[3]}</p> : null}
              <a className="text-link" href={`#authority-${resource.candidate_id}`}>Review exact resources</a>
            </article>

            <article>
              <div className="explosive-power-path__heading">
                <span>3</span>
                <div>
                  <p className="eyebrow">Bound the first dose</p>
                  <h3>{construction.release_label}</h3>
                </div>
                <span className={`status-badge status-badge--${review.construction.status}`}>
                  {review.construction.status}
                </span>
              </div>
              <p>{construction.summary}</p>
              <ul>{construction.governs.map((value) => <li key={value}>{value}</li>)}</ul>
              <a className="text-link" href={`#authority-${construction.slug}`}>Review exact construction rules</a>
            </article>
          </div>

          <div className="assessment-candidate-meaning explosive-power-why">
            <section>
              <h3>What the science supports</h3>
              <p>{construction.authority_basis.scientific_support}</p>
              {resource.evidence[0] ? (
                <a className="text-link" href={resource.evidence[0].source_url} target="_blank" rel="noreferrer">
                  Open the reviewed source
                </a>
              ) : null}
            </section>
            <section>
              <h3>What AGAS chose provisionally</h3>
              <p>{construction.authority_basis.engineering_prior}</p>
              <p>
                The floor, exercise resolution, weekly envelope, dose, rest, effort range, and
                progression caps remain separately reviewable engineering choices.
              </p>
            </section>
          </div>

          <aside className="review-boundary">
            <strong>Approval still happens on the exact cards below.</strong>
            <span>
              Ratify the floor before the resource bundle, and the resource bundle before the
              construction rules. A blocked status is an enforced dependency, not permission to
              skip ahead. Current readiness, symptoms, environment, and recent jump exposure remain
              controlling gates after approval.
            </span>
          </aside>
        </>
      ) : loading ? (
        <p className="planning-queue-empty">Loading the connected explosive-power review…</p>
      ) : null}

      {message ? <p className="form-error" role="status">{message}</p> : null}
    </section>
  );
}
