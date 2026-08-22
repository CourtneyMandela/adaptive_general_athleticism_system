"use client";

import { FormEvent, useMemo, useState } from "react";

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
import {
  PostSessionSafetyForm,
  ProgressionEvaluationButton,
  SafetyCheckForm,
  WorkoutLogForm,
} from "./session-actions";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const configuredAthleteId = process.env.NEXT_PUBLIC_AGAS_ATHLETE_ID ?? "";
const configuredSafetyPolicyId = process.env.NEXT_PUBLIC_AGAS_SAFETY_POLICY_ID ?? "";

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
  safetyPolicyId,
  onSaved,
}: {
  session: PlannedSessionProjection;
  asOf: string;
  weeklyPlanId: string;
  safetyPolicyId: string;
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
            <PostSessionSafetyForm
              apiBaseUrl={apiBaseUrl}
              weeklyPlanId={weeklyPlanId}
              safetyPolicyId={safetyPolicyId}
              session={session}
              onSaved={onSaved}
            />
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
                        {prescription.progression_action.status === "ready" &&
                        prescription.progression_action.progression_policy_id ? (
                          <ProgressionEvaluationButton
                            apiBaseUrl={apiBaseUrl}
                            executionId={session.execution!.execution_id}
                            prescriptionId={prescription.prescription_id}
                            progressionPolicyId={
                              prescription.progression_action.progression_policy_id
                            }
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
          <SafetyCheckForm
            apiBaseUrl={apiBaseUrl}
            weeklyPlanId={weeklyPlanId}
            safetyPolicyId={safetyPolicyId}
            session={session}
            onSaved={onSaved}
          />
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
  const [safetyPolicyInput, setSafetyPolicyInput] = useState(configuredSafetyPolicyId);
  const [athleteId, setAthleteId] = useState("");
  const [safetyPolicyId, setSafetyPolicyId] = useState("");
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

  const completedSessions = useMemo(
    () =>
      projection?.week?.sessions.filter((session) => session.status === "completed").length ?? 0,
    [projection],
  );

  function connectAthlete(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = athleteInput.trim();
    if (!isUuid(normalized)) {
      setMessage("Enter a valid athlete ID from the persisted backend.");
      setState("error");
      return;
    }
    const normalizedPolicy = safetyPolicyInput.trim();
    if (!isUuid(normalizedPolicy)) {
      setMessage("Enter a valid reviewed safety policy ID from the persisted backend.");
      setState("error");
      return;
    }
    setAthleteId(normalized);
    setSafetyPolicyId(normalizedPolicy);
    void load(normalized, asOf);
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
            Connect an existing athlete and reviewed safety policy. This daily-use slice can inspect
            the persisted week, evaluate a pre-session report, and record actual work.
          </p>
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
            <label htmlFor="safety-policy-id">Safety policy ID</label>
            <input
              id="safety-policy-id"
              name="safety-policy-id"
              value={safetyPolicyInput}
              onChange={(event) => setSafetyPolicyInput(event.target.value)}
              placeholder="00000000-0000-4000-8000-000000000000"
              autoComplete="off"
            />
            <p className="form-help">Temporary local setup until onboarding and policy assignment exist.</p>
            <button type="submit">Open current week</button>
          </form>
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
            setSafetyPolicyId("");
            setProjection(null);
            setState("setup");
          }}
        >
          Change athlete
        </button>
      </header>

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
          <p className="eyebrow">No scheduled week</p>
          <h2>There is no persisted plan covering {asOf}.</h2>
          <p>AGAS will not invent a workout to fill this gap.</p>
        </section>
      ) : null}

      {state === "ready" && projection?.week ? (
        <>
          <section className="week-summary" aria-labelledby="week-title">
            <div>
              <p className="eyebrow">Block week {projection.week.block_week}</p>
              <h2 id="week-title">
                {formatWeekRange(projection.week.week_start, projection.week.week_end)}
              </h2>
            </div>
            <div className="week-stat">
              <strong>
                {completedSessions}/{projection.week.sessions.length}
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
                safetyPolicyId={safetyPolicyId}
                onSaved={() => load(athleteId, asOf)}
              />
            ))}
          </section>
        </>
      ) : null}
    </main>
  );
}
