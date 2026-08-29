"use client";

import { FormEvent, useState } from "react";

import {
  fetchCurrentWeek,
  formatDose,
  isUuid,
  localIsoDate,
  progressionOutcomeLabel,
  safetyOutcomeLabel,
  sessionStatusLabel,
  shiftIsoDate,
  type CurrentWeekProjection,
  type PlannedSessionProjection,
} from "@/lib/current-week";
import { OnboardingForm } from "./onboarding-form";
import { AssessmentPanel } from "./assessment-panel";
import { AthleticDashboardPanel } from "./athletic-dashboard-panel";
import { EnvironmentPanel } from "./environment-panel";
import { PlanningStatusPanel } from "./planning-status-panel";
import {
  PostSessionSafetyForm,
  ProgressionEvaluationButton,
  SafetyCheckForm,
  WorkoutLogForm,
} from "./session-actions";
import { WeeklyReview } from "./weekly-review";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const configuredAthleteId = process.env.NEXT_PUBLIC_AGAS_ATHLETE_ID ?? "";

function formatWeekRange(start: string, end: string): string {
  const formatter = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" });
  return `${formatter.format(new Date(`${start}T12:00:00`))} – ${formatter.format(new Date(`${end}T12:00:00`))}`;
}

function formatSessionTime(startsAt: string): string {
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(startsAt));
}

function SessionCard({
  session,
  asOf,
  weeklyPlanId,
  hasSafetyPolicyAssignment,
  onSaved,
}: {
  session: PlannedSessionProjection;
  asOf: string;
  weeklyPlanId: string;
  hasSafetyPolicyAssignment: boolean;
  onSaved: () => Promise<void>;
}) {
  const isToday = session.starts_at.slice(0, 10) === asOf;
  return (
    <article className={`session-card${isToday ? " session-card--today" : ""}`}>
      <header className="session-card__header">
        <div>
          <p className="session-card__time">{formatSessionTime(session.starts_at)}</p>
          <h3>{session.session_name}</h3>
          <p className="session-card__meta">
            {session.planned_duration_minutes} min · {session.environment_name}
          </p>
        </div>
        <span className={`status-badge status-badge--${session.status}`}>
          {sessionStatusLabel(session.status)}
        </span>
      </header>

      {session.pre_session_safety?.required_modifications.length ? (
        <div className="safety-note">
          <strong>Required modifications</strong>
          <span>{session.pre_session_safety.required_modifications.join(", ")}</span>
        </div>
      ) : null}

      <ol className="prescription-list">
        {session.prescriptions.map((prescription) => (
          <li key={prescription.prescription_id}>
            <span className="exercise-order" aria-hidden="true">
              {String.fromCharCode(64 + prescription.order_index)}
            </span>
            <div className="exercise-copy">
              <div className="exercise-line">
                <strong>{prescription.exercise_name}</strong>
                <span>{formatDose(prescription)}</span>
              </div>
              <p>
                {prescription.intensity_targets.join(" · ")} · {prescription.rest_seconds}s rest
              </p>
              {prescription.adherence ? (
                <p className="completion-line">
                  {prescription.adherence.performed_sets}/{prescription.adherence.prescribed_sets}{" "}
                  sets · {Math.round(prescription.adherence.dose_completion_ratio * 100)}% dose
                </p>
              ) : null}
              <details>
                <summary>Why this is here</summary>
                <p>
                  <strong>{prescription.adaptation_name}.</strong>{" "}
                  {prescription.reason_for_inclusion}
                </p>
              </details>
            </div>
          </li>
        ))}
      </ol>

      {session.execution ? (
        <div className="session-actions">
          <footer className="session-result">
            <span>Logged</span>
            <span>
              {session.execution.session_rpe === null
                ? "Effort not reported"
                : `Session RPE ${session.execution.session_rpe}`}
            </span>
          </footer>
          {session.execution.post_session_safety_outcomes.length === 0 ? (
            hasSafetyPolicyAssignment ? (
              <PostSessionSafetyForm
                apiBaseUrl={apiBaseUrl}
                weeklyPlanId={weeklyPlanId}
                session={session}
                onSaved={onSaved}
              />
            ) : (
              <p className="session-pending">
                A reviewed safety-policy assignment is required before recovery closure.
              </p>
            )
          ) : (
            <section className="closure-panel" aria-label="Post-session review">
              <p className="eyebrow">Recovery report</p>
              <p>
                {session.execution.post_session_safety_outcomes
                  .map(safetyOutcomeLabel)
                  .join(" · ")}
              </p>
              <ul className="progression-list">
                {session.prescriptions.map((prescription) => (
                  <li key={prescription.prescription_id}>
                    <strong>{prescription.exercise_name}</strong>
                    {prescription.progression ? (
                      <span>
                        {progressionOutcomeLabel(prescription.progression.outcome)}
                        {prescription.progression.adjustment_description
                          ? ` — ${prescription.progression.adjustment_description}`
                          : ""}
                      </span>
                    ) : (
                      <>
                        <span>{prescription.progression_action.reason}</span>
                        {prescription.progression_action.status === "ready" ? (
                          <ProgressionEvaluationButton
                            apiBaseUrl={apiBaseUrl}
                            executionId={session.execution!.execution_id}
                            prescriptionId={prescription.prescription_id}
                            onSaved={onSaved}
                          />
                        ) : null}
                      </>
                    )}
                  </li>
                ))}
              </ul>
              {session.prescriptions.some(
                (item) =>
                  item.progression === null && item.progression_action.status !== "ready",
              ) ? (
                <p className="form-help">
                  Exposure targets, duration budgets, missing policies, and ambiguous policies
                  require governed configuration; the PWA will not guess them.
                </p>
              ) : null}
            </section>
          )}
        </div>
      ) : (
        <div className="session-actions">
          {hasSafetyPolicyAssignment ? (
            <SafetyCheckForm
              apiBaseUrl={apiBaseUrl}
              weeklyPlanId={weeklyPlanId}
              session={session}
              onSaved={onSaved}
            />
          ) : (
            <p className="session-pending">
              A reviewed safety policy must be assigned before a safety check can authorize this
              session.
            </p>
          )}
          {session.pre_session_safety?.outcome === "proceed" ||
          session.pre_session_safety?.outcome === "modify" ? (
            <WorkoutLogForm
              apiBaseUrl={apiBaseUrl}
              weeklyPlanId={weeklyPlanId}
              session={session}
              onSaved={onSaved}
            />
          ) : session.pre_session_safety ? (
            <p className="session-pending">
              This safety decision does not authorize an ordinary workout. Update the safety check
              only if your reported state has genuinely changed.
            </p>
          ) : null}
        </div>
      )}
    </article>
  );
}

export function CurrentWeekDashboard() {
  const [athleteInput, setAthleteInput] = useState(configuredAthleteId);
  const [athleteId, setAthleteId] = useState("");
  const [asOf, setAsOf] = useState(localIsoDate);
  const [projection, setProjection] = useState<CurrentWeekProjection | null>(null);
  const [state, setState] = useState<"setup" | "loading" | "ready" | "error">("setup");
  const [message, setMessage] = useState("");

  async function load(nextAthleteId: string, nextAsOf: string) {
    setState("loading");
    setMessage("");
    try {
      const result = await fetchCurrentWeek(apiBaseUrl, nextAthleteId, nextAsOf);
      setProjection(result);
      setState("ready");
    } catch (error) {
      setProjection(null);
      setMessage(error instanceof Error ? error.message : "Unable to load the current week.");
      setState("error");
    }
  }

  function connectAthlete(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = athleteInput.trim();
    if (!isUuid(normalized)) {
      setMessage("Enter a valid athlete ID from the persisted backend.");
      setState("error");
      return;
    }
    setAthleteId(normalized);
    void load(normalized, asOf);
  }

  function openCreatedAthlete(createdAthleteId: string) {
    setAthleteInput(createdAthleteId);
    setAthleteId(createdAthleteId);
    void load(createdAthleteId, asOf);
  }

  function selectDate(nextDate: string) {
    setAsOf(nextDate);
    void load(athleteId, nextDate);
  }

  if (!athleteId) {
    return (
      <main className="setup-shell">
        <section className="setup-card" aria-labelledby="setup-title">
          <p className="eyebrow">Adaptive General Athleticism System</p>
          <h1 id="setup-title">Your training week, with the why intact.</h1>
          <p className="lede">
            Create a non-sensitive athlete profile and record the places and equipment available to
            you. AGAS keeps your report as provenance-bearing input; it will not turn it into an
            unsupported fitness score or invented workout.
          </p>
          <OnboardingForm apiBaseUrl={apiBaseUrl} onCreated={openCreatedAthlete} />
          <details className="existing-profile">
            <summary>Connect an existing development profile</summary>
            <form onSubmit={connectAthlete} className="athlete-form">
              <label htmlFor="athlete-id">Athlete ID</label>
              <input
                id="athlete-id"
                name="athlete-id"
                value={athleteInput}
                onChange={(event) => setAthleteInput(event.target.value)}
                placeholder="00000000-0000-4000-8000-000000000000"
                autoComplete="off"
              />
              <p className="form-help">
                This developer path requires an owned athlete ID. Any reviewed safety-policy
                assignment is resolved from the backend rather than entered here.
              </p>
              <button type="submit">Open current week</button>
            </form>
          </details>
          {message ? <p className="form-error">{message}</p> : null}
        </section>
      </main>
    );
  }

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">AGAS · Current week</p>
          <h1>{projection?.athlete_display_name ?? "Training week"}</h1>
        </div>
        <button
          type="button"
          className="text-button"
          onClick={() => {
            setAthleteId("");
            setProjection(null);
            setState("setup");
          }}
        >
          Change athlete
        </button>
      </header>

      <AssessmentPanel apiBaseUrl={apiBaseUrl} athleteId={athleteId} />
      <AthleticDashboardPanel apiBaseUrl={apiBaseUrl} athleteId={athleteId} />
      <EnvironmentPanel apiBaseUrl={apiBaseUrl} athleteId={athleteId} />
      <PlanningStatusPanel apiBaseUrl={apiBaseUrl} athleteId={athleteId} />

      <nav className="week-nav" aria-label="Week navigation">
        <button type="button" onClick={() => selectDate(shiftIsoDate(asOf, -7))}>
          ← Previous
        </button>
        <label>
          Week containing
          <input type="date" value={asOf} onChange={(event) => selectDate(event.target.value)} />
        </label>
        <button type="button" onClick={() => selectDate(shiftIsoDate(asOf, 7))}>
          Next →
        </button>
      </nav>

      {state === "loading" ? (
        <section className="state-card" aria-live="polite">
          <span className="loader" aria-hidden="true" />
          <p>Loading the persisted week…</p>
        </section>
      ) : null}

      {state === "error" ? (
        <section className="state-card state-card--error" role="alert">
          <h2>We couldn’t load this week.</h2>
          <p>{message}</p>
          <button type="button" onClick={() => void load(athleteId, asOf)}>
            Try again
          </button>
        </section>
      ) : null}

      {state === "ready" && projection?.week === null ? (
        <section className="state-card">
          <p className="eyebrow">Profile saved · No scheduled week</p>
          <h2>There is no persisted plan covering {asOf}.</h2>
          {projection.safety_policy_assignment ? (
            <p>
              Safety policy {projection.safety_policy_assignment.policy_version} is assigned. An
              assessment and governed first-plan workflow are still required; AGAS will not invent
              a workout to fill the gap.
            </p>
          ) : (
            <p>
              AGAS will not invent a workout to fill this gap. A reviewed safety-policy assignment,
              assessment, and governed first-plan workflow are still required.
            </p>
          )}
        </section>
      ) : null}

      {state === "ready" && projection?.week ? (
        <>
          {projection.safety_policy_assignment ? (
            <section className="safety-note" aria-label="Assigned safety policy">
              <strong>Reviewed safety policy</strong>
              <span>{projection.safety_policy_assignment.policy_version}</span>
            </section>
          ) : (
            <section className="state-card state-card--error" role="alert">
              <h2>Safety checks are unavailable.</h2>
              <p>
                This athlete has no governed safety-policy assignment. Scheduled work remains
                visible, but the PWA cannot authorize a session.
              </p>
            </section>
          )}
          <section className="week-summary" aria-labelledby="week-title">
            <div>
              <p className="eyebrow">Block week {projection.week.block_week}</p>
              <h2 id="week-title">
                {formatWeekRange(projection.week.week_start, projection.week.week_end)}
              </h2>
            </div>
            <div className="week-stat">
              <strong>
                {projection.week.review.completed_sessions}/
                {projection.week.review.scheduled_sessions}
              </strong>
              <span>sessions completed</span>
            </div>
          </section>
          <section className="session-grid" aria-label="Scheduled sessions">
            {projection.week.sessions.map((session) => (
              <SessionCard
                key={session.planned_session_id}
                session={session}
                asOf={asOf}
                weeklyPlanId={projection.week!.weekly_plan_id}
                hasSafetyPolicyAssignment={projection.safety_policy_assignment !== null}
                onSaved={() => load(athleteId, asOf)}
              />
            ))}
          </section>
          <WeeklyReview
            key={projection.week.weekly_plan_id}
            week={projection.week}
            apiBaseUrl={apiBaseUrl}
            athleteId={athleteId}
            onWeekUpdated={() => load(athleteId, asOf)}
            onWeekPrepared={async (nextWeekStart) => {
              setAsOf(nextWeekStart);
              await load(athleteId, nextWeekStart);
            }}
          />
        </>
      ) : null}
    </main>
  );
}
