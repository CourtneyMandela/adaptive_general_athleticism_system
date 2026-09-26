"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { fetchAssessmentGovernanceCandidates } from "@/lib/assessment-governance";
import {
  selectAerobicAuthorityReview,
  type AerobicAuthorityReview,
} from "@/lib/aerobic-authority-review";
import { athleteReviewHref } from "@/lib/athlete-navigation";
import { fetchCompetencyFloorCandidates } from "@/lib/competency-floor-governance";
import { fetchResourceGovernanceCandidates } from "@/lib/resource-governance";
import { fetchTrainingConstructionCandidates } from "@/lib/training-construction-governance";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function AerobicAuthorityReviewClient({ athleteId }: { athleteId?: string }) {
  const [review, setReview] = useState<AerobicAuthorityReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      const [assessments, floors, resources, construction] = await Promise.all([
        fetchAssessmentGovernanceCandidates(apiBaseUrl),
        fetchCompetencyFloorCandidates(apiBaseUrl),
        fetchResourceGovernanceCandidates(apiBaseUrl),
        fetchTrainingConstructionCandidates(apiBaseUrl),
      ]);
      setReview(selectAerobicAuthorityReview(assessments, floors, resources, construction));
    } catch (error) {
      setReview(null);
      setMessage(error instanceof Error ? error.message : "Unable to load the aerobic review.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    void Promise.all([
      fetchAssessmentGovernanceCandidates(apiBaseUrl),
      fetchCompetencyFloorCandidates(apiBaseUrl),
      fetchResourceGovernanceCandidates(apiBaseUrl),
      fetchTrainingConstructionCandidates(apiBaseUrl),
    ])
      .then(([assessments, floors, resources, construction]) => {
        if (active) {
          setReview(selectAerobicAuthorityReview(assessments, floors, resources, construction));
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(error instanceof Error ? error.message : "Unable to load the aerobic review.");
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

  const assessment = review?.assessment.candidate;
  const floor = review?.floor.candidate;
  const resource = review?.resource.candidate;
  const construction = review?.construction.candidate;
  const assessmentHref = assessment
    ? `${athleteReviewHref("/review/assessments", athleteId)}#candidate-${assessment.candidate_id}`
    : athleteReviewHref("/review/assessments", athleteId);

  return (
    <section className="planning-queue-summary authority-review" aria-labelledby="aerobic-review-title">
      <header>
        <div>
          <p className="eyebrow">Concise why · provisional aerobic-capacity path</p>
          <h2 id="aerobic-review-title">Why AGAS may propose aerobic-base training</h2>
        </div>
        <button type="button" className="secondary-button" disabled={loading} onClick={() => void refresh()}>
          {loading ? "Loading…" : "Refresh path"}
        </button>
      </header>

      {review && assessment && floor && resource && construction ? (
        <>
          <p>
            This view connects one direct field observation to a provisional need, feasible means,
            and bounded starting dose. It composes four exact candidates without merging their
            approvals or creating an athlete plan.
          </p>

          <div className="authority-path authority-path--four" aria-label="Aerobic authority path">
            <article>
              <div className="authority-path__heading">
                <span>1</span>
                <div>
                  <p className="eyebrow">Measure direct capacity</p>
                  <h3>{assessment.release_label}</h3>
                </div>
                <span className={`status-badge status-badge--${review.assessment.status}`}>
                  {review.assessment.status}
                </span>
              </div>
              <p className="authority-path__value">12 minutes · direct meters</p>
              <p>{assessment.measures}</p>
              <p>No laboratory VO2 conversion or universal fitness grade is inferred.</p>
              <Link className="text-link" href={assessmentHref}>Review exact assessment</Link>
            </article>

            <article>
              <div className="authority-path__heading">
                <span>2</span>
                <div>
                  <p className="eyebrow">Identify a provisional need</p>
                  <h3>{floor.release_label}</h3>
                </div>
                <span className={`status-badge status-badge--${review.floor.status}`}>
                  {review.floor.status}
                </span>
              </div>
              <p className="authority-path__value">{floor.threshold} {floor.unit_or_scale}</p>
              <p>{floor.authority_basis.numeric_value_explanation}</p>
              <a className="text-link" href={`#authority-${floor.slug}`}>Review exact floor</a>
            </article>

            <article>
              <div className="authority-path__heading">
                <span>3</span>
                <div>
                  <p className="eyebrow">Choose feasible means</p>
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
              <div className="authority-path__heading">
                <span>4</span>
                <div>
                  <p className="eyebrow">Bound duration and progression</p>
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

          <div className="assessment-candidate-meaning authority-review__why">
            <section>
              <h3>What the science supports</h3>
              {assessment.evidence[0] ? <p>{assessment.evidence[0].finding}</p> : null}
              <p>{construction.authority_basis.scientific_support}</p>
              {assessment.evidence[0] ? (
                <a className="text-link" href={assessment.evidence[0].source_url} target="_blank" rel="noreferrer">
                  Open the field-test validity source
                </a>
              ) : null}
            </section>
            <section>
              <h3>What AGAS chose provisionally</h3>
              <p>{floor.authority_basis.numeric_value_explanation}</p>
              <p>{construction.authority_basis.engineering_prior}</p>
              <p>
                The floor, modality, weekly envelope, starting duration, progression gate, ceiling,
                and response threshold remain separately reviewable engineering choices.
              </p>
            </section>
          </div>

          <aside className="review-boundary">
            <strong>Approval still happens on four exact records.</strong>
            <span>
              Review the assessment on its governance page, then the floor, resource, and
              construction cards below. A blocked status is an enforced dependency. Current
              readiness, symptoms, measured environment, and walking or running familiarity remain
              controlling gates after approval.
            </span>
          </aside>
        </>
      ) : loading ? (
        <p className="planning-queue-empty">Loading the connected aerobic review…</p>
      ) : null}

      {message ? <p className="form-error" role="status">{message}</p> : null}
    </section>
  );
}
