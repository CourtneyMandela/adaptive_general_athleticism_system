"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  buildProgressionEvaluationCommand,
  buildExecutionCommand,
  createPrescriptionLogDrafts,
  pwaProvenance,
  submitSafetyCheck,
  submitSessionExecution,
  submitProgressionEvaluation,
  type Confidence,
  type PlannedSessionProjection,
  type PrescriptionLogDraft,
} from "@/lib/current-week";
import { formatRestTime, remainingRestSeconds } from "@/lib/rest-timer";

const confidenceOptions: Array<{ value: Confidence; label: string }> = [
  { value: "moderate", label: "Moderate confidence" },
  { value: "high", label: "High confidence" },
  { value: "low", label: "Low confidence" },
  { value: "unknown", label: "Unknown confidence" },
];

function localDateTime(value: string): string {
  const source = new Date(value);
  const offset = source.getTimezoneOffset() * 60_000;
  return new Date(source.getTime() - offset).toISOString().slice(0, 19);
}

function parseOptionalRpe(value: string): number | null {
  return value === "" ? null : Number(value);
}

function RestTimer({ restSeconds, enabled }: { restSeconds: number; enabled: boolean }) {
  const [deadline, setDeadline] = useState<number | null>(null);
  const [remaining, setRemaining] = useState(restSeconds);

  useEffect(() => {
    if (deadline === null) return;
    const update = () => {
      const next = remainingRestSeconds(deadline, Date.now());
      setRemaining(next);
      if (next === 0) setDeadline(null);
    };
    update();
    const interval = window.setInterval(update, 250);
    return () => window.clearInterval(interval);
  }, [deadline]);

  function start() {
    setRemaining(restSeconds);
    setDeadline(Date.now() + restSeconds * 1000);
  }

  function cancel() {
    setDeadline(null);
    setRemaining(restSeconds);
  }

  const running = deadline !== null;
  const complete = !running && remaining === 0;
  return (
    <div className={`rest-timer${complete ? " rest-timer--complete" : ""}`}>
      <span aria-live="polite">
        {running ? `Rest ${formatRestTime(remaining)}` : complete ? "Rest complete" : `Rest ${formatRestTime(restSeconds)}`}
      </span>
      <button type="button" disabled={!enabled || restSeconds === 0} onClick={start}>
        {running || complete ? "Restart" : "Start rest"}
      </button>
      {running ? <button type="button" className="text-button" onClick={cancel}>Cancel</button> : null}
    </div>
  );
}

type WorkoutPhase = "ready" | "active" | "review";

interface WorkoutLogState {
  phase: WorkoutPhase;
  drafts: PrescriptionLogDraft[];
  startedAt: string;
  endedAt: string;
  sessionRpe: string;
  note: string;
  reliability: Confidence;
}

interface StoredWorkoutLog extends WorkoutLogState {
  version: 1;
  safetyDecisionId: string;
  prescriptionSignature: string;
}

function prescriptionSignature(session: PlannedSessionProjection): string {
  return session.prescriptions
    .map((prescription) => `${prescription.prescription_id}:${prescription.sets}`)
    .join("|");
}

function blankWorkoutLog(session: PlannedSessionProjection): WorkoutLogState {
  return {
    phase: "ready",
    drafts: createPrescriptionLogDrafts(session),
    startedAt: "",
    endedAt: "",
    sessionRpe: "",
    note: "",
    reliability: "moderate",
  };
}

function isOptionalRpe(value: unknown): value is number | null {
  return value === null || (
    typeof value === "number"
    && Number.isFinite(value)
    && value >= 0
    && value <= 10
  );
}

function hasCompatibleDrafts(
  value: unknown,
  session: PlannedSessionProjection,
): value is PrescriptionLogDraft[] {
  if (!Array.isArray(value) || value.length !== session.prescriptions.length) return false;
  return value.every((candidate, prescriptionIndex) => {
    if (!candidate || typeof candidate !== "object") return false;
    const draft = candidate as Partial<PrescriptionLogDraft>;
    const prescription = session.prescriptions[prescriptionIndex];
    if (
      draft.prescriptionId !== prescription.prescription_id
      || !isOptionalRpe(draft.itemRpe)
      || !Array.isArray(draft.sets)
      || draft.sets.length !== prescription.sets
    ) return false;
    return draft.sets.every((candidateSet, setIndex) => (
      candidateSet.setIndex === setIndex + 1
      && typeof candidateSet.performed === "boolean"
      && Number.isInteger(candidateSet.actualDose)
      && candidateSet.actualDose >= 0
      && isOptionalRpe(candidateSet.effortRpe)
      && (
        candidateSet.techniqueConstraintMet === null
        || typeof candidateSet.techniqueConstraintMet === "boolean"
      )
    ));
  });
}

export function SafetyCheckForm({
  apiBaseUrl,
  weeklyPlanId,
  session,
  onSaved,
}: {
  apiBaseUrl: string;
  weeklyPlanId: string;
  session: PlannedSessionProjection;
  onSaved: () => Promise<void>;
}) {
  const [readiness, setReadiness] = useState<"ready" | "limited" | "not_ready">("ready");
  const [unusualSoreness, setUnusualSoreness] = useState(false);
  const [sleepDisruption, setSleepDisruption] = useState(false);
  const [scheduleLimitation, setScheduleLimitation] = useState(false);
  const [concerningSymptom, setConcerningSymptom] = useState(false);
  const [note, setNote] = useState("");
  const [reliability, setReliability] = useState<Confidence>("moderate");
  const [state, setState] = useState<"idle" | "saving" | "error">("idle");
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (concerningSymptom) return;
    setState("saving");
    setMessage("");
    const reportedAt = new Date();
    try {
      await submitSafetyCheck(apiBaseUrl, weeklyPlanId, session.planned_session_id, {
        timing: "pre_session",
        readiness,
        unusual_soreness: unusualSoreness,
        major_sleep_disruption: sleepDisruption,
        major_schedule_limitation: scheduleLimitation,
        signals: [],
        note: note.trim() || null,
        reported_at: reportedAt.toISOString(),
        decided_at: reportedAt.toISOString(),
        reliability,
        provenance: pwaProvenance,
      });
      await onSaved();
      setState("idle");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save the safety check.");
      setState("error");
    }
  }

  return (
    <details className="action-panel" open={!session.pre_session_safety}>
      <summary>{session.pre_session_safety ? "Update safety check" : "Complete safety check"}</summary>
      <form className="action-form" onSubmit={submit}>
        <fieldset disabled={state === "saving"}>
          <legend>How are you arriving today?</legend>
          <label>
            Readiness
            <select value={readiness} onChange={(event) => setReadiness(event.target.value as typeof readiness)}>
              <option value="ready">Ready</option>
              <option value="limited">Limited</option>
              <option value="not_ready">Not ready</option>
            </select>
          </label>
          <div className="check-list">
            <label><input type="checkbox" checked={unusualSoreness} onChange={(event) => setUnusualSoreness(event.target.checked)} />Unusual soreness</label>
            <label><input type="checkbox" checked={sleepDisruption} onChange={(event) => setSleepDisruption(event.target.checked)} />Major sleep disruption</label>
            <label><input type="checkbox" checked={scheduleLimitation} onChange={(event) => setScheduleLimitation(event.target.checked)} />Major schedule limitation</label>
            <label><input type="checkbox" checked={concerningSymptom} onChange={(event) => setConcerningSymptom(event.target.checked)} />Pain or another concerning symptom requiring assessment</label>
          </div>
          {concerningSymptom ? (
            <p className="safety-stop" role="alert">
              Normal workout flow is paused. This prototype cannot classify symptoms or provide medical guidance. Seek appropriate evaluation when a symptom is concerning.
            </p>
          ) : null}
          <label>
            Context note <span>(optional)</span>
            <textarea value={note} onChange={(event) => setNote(event.target.value)} rows={2} />
          </label>
          <label>
            Report confidence
            <select value={reliability} onChange={(event) => setReliability(event.target.value as Confidence)}>
              {confidenceOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <button type="submit" disabled={concerningSymptom || state === "saving"}>
            {state === "saving" ? "Checking…" : "Save and evaluate"}
          </button>
          {message ? <p className="form-error" role="alert">{message}</p> : null}
        </fieldset>
      </form>
    </details>
  );
}

export function WorkoutLogForm({
  apiBaseUrl,
  weeklyPlanId,
  session,
  onSaved,
}: {
  apiBaseUrl: string;
  weeklyPlanId: string;
  session: PlannedSessionProjection;
  onSaved: () => Promise<void>;
}) {
  const safety = session.pre_session_safety!;
  const storageKey = `agas:workout-draft:${session.planned_session_id}`;
  const expectedSignature = useMemo(() => prescriptionSignature(session), [session]);
  const [workout, setWorkout] = useState<WorkoutLogState>(() => blankWorkoutLog(session));
  const [state, setState] = useState<"idle" | "saving" | "error">("idle");
  const [message, setMessage] = useState("");
  const allNotStarted = workout.drafts.every((draft) =>
    draft.sets.every((setDraft) => !setDraft.performed),
  );

  function persist(next: WorkoutLogState) {
    setWorkout(next);
    const stored: StoredWorkoutLog = {
      ...next,
      version: 1,
      safetyDecisionId: safety.decision_id,
      prescriptionSignature: expectedSignature,
    };
    window.localStorage.setItem(storageKey, JSON.stringify(stored));
  }

  function updateWorkout(update: (current: WorkoutLogState) => WorkoutLogState) {
    persist(update(workout));
  }

  function startWorkout() {
    persist({
      ...blankWorkoutLog(session),
      phase: "active",
      startedAt: localDateTime(new Date().toISOString()),
    });
    setMessage("");
  }

  function resumeWorkout() {
    setMessage("");
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (!raw) throw new Error("No unfinished workout is saved on this device.");
      const stored = JSON.parse(raw) as Partial<StoredWorkoutLog>;
      if (
        stored.version !== 1
        || stored.safetyDecisionId !== safety.decision_id
        || stored.prescriptionSignature !== expectedSignature
        || (stored.phase !== "active" && stored.phase !== "review")
        || !hasCompatibleDrafts(stored.drafts, session)
      ) {
        throw new Error("The saved workout does not match this authorized session.");
      }
      setWorkout({
        phase: stored.phase,
        drafts: stored.drafts,
        startedAt: typeof stored.startedAt === "string" ? stored.startedAt : "",
        endedAt: typeof stored.endedAt === "string" ? stored.endedAt : "",
        sessionRpe: typeof stored.sessionRpe === "string" ? stored.sessionRpe : "",
        note: typeof stored.note === "string" ? stored.note : "",
        reliability: ["unknown", "low", "moderate", "high"].includes(stored.reliability ?? "")
          ? stored.reliability as Confidence
          : "moderate",
      });
      setState("idle");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to restore the saved workout.");
      setState("error");
    }
  }

  function updateSet(
    prescriptionId: string,
    setIndex: number,
    update: Partial<PrescriptionLogDraft["sets"][number]>,
  ) {
    updateWorkout((current) => ({
      ...current,
      drafts: current.drafts.map((draft) => draft.prescriptionId === prescriptionId
        ? {
            ...draft,
            sets: draft.sets.map((setDraft) => setDraft.setIndex === setIndex
              ? { ...setDraft, ...update }
              : setDraft),
          }
        : draft),
    }));
  }

  function updateItemRpe(prescriptionId: string, itemRpe: number | null) {
    updateWorkout((current) => ({
      ...current,
      drafts: current.drafts.map((draft) => draft.prescriptionId === prescriptionId
        ? { ...draft, itemRpe }
        : draft),
    }));
  }

  function finishWorkout() {
    updateWorkout((current) => ({
      ...current,
      phase: "review",
      endedAt: localDateTime(new Date(Math.max(
        Date.now(),
        new Date(current.startedAt).getTime() + 60_000,
      )).toISOString()),
    }));
  }

  function recordNotStarted() {
    persist({ ...blankWorkoutLog(session), phase: "review" });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("saving");
    setMessage("");
    try {
      const command = buildExecutionCommand({
        session,
        drafts: workout.drafts,
        safetyDecisionId: safety.decision_id,
        requiredModifications: safety.required_modifications,
        startedAt: allNotStarted ? null : new Date(workout.startedAt),
        endedAt: allNotStarted ? null : new Date(workout.endedAt),
        sessionRpe: parseOptionalRpe(workout.sessionRpe),
        note: workout.note,
        reliability: workout.reliability,
      });
      await submitSessionExecution(apiBaseUrl, weeklyPlanId, session.planned_session_id, command);
      window.localStorage.removeItem(storageKey);
      await onSaved();
      setState("idle");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save the workout log.");
      setState("error");
    }
  }

  const minimumStart = localDateTime(safety.decided_at);
  return (
    <details className="action-panel" open={workout.phase !== "ready"}>
      <summary>{workout.phase === "ready" ? "Train this session" : "Workout in progress"}</summary>
      {workout.phase === "ready" ? (
        <section className="workout-launcher">
          <p>
            Follow the exact scheduled work above. Set-by-set results stay on this device until
            you review and save the completed session.
          </p>
          <div className="workout-launcher__actions">
            <button type="button" onClick={startWorkout}>Start workout</button>
            <button type="button" className="secondary-button" onClick={resumeWorkout}>
              Resume saved workout
            </button>
            <button type="button" className="text-button" onClick={recordNotStarted}>
              Record that I did not start
            </button>
          </div>
          {message ? <p className="form-error" role="alert">{message}</p> : null}
        </section>
      ) : (
      <form className="action-form live-workout" onSubmit={submit}>
        <fieldset disabled={state === "saving"}>
          <legend>{workout.phase === "active" ? "Train set by set" : "Review what happened"}</legend>
          <p className="form-help">
            Check a set only after performing it. The prescribed dose is prefilled, but the saved
            record must reflect what actually happened.
          </p>
          <div className="execution-items">
            {session.prescriptions.map((prescription, index) => {
              const draft = workout.drafts[index];
              const unit = prescription.repetitions_per_set === null ? "seconds" : "reps";
              return (
                <section key={prescription.prescription_id} className="execution-item">
                  <header className="execution-item__header">
                    <div>
                      <strong>{prescription.exercise_name}</strong>
                      <span>{prescription.sets} sets · {prescription.rest_seconds}s rest</span>
                    </div>
                    <span>{prescription.intensity_targets.join(" · ")}</span>
                  </header>
                  <div className="set-log-list">
                    {draft.sets.map((setDraft) => (
                      <section
                        key={setDraft.setIndex}
                        className={`set-log${setDraft.performed ? " set-log--done" : ""}`}
                      >
                        <label className="set-complete">
                          <input
                            type="checkbox"
                            checked={setDraft.performed}
                            onChange={(event) => updateSet(
                              draft.prescriptionId,
                              setDraft.setIndex,
                              { performed: event.target.checked },
                            )}
                          />
                          Set {setDraft.setIndex} done
                        </label>
                        <label>
                          Actual {unit}
                          <input
                            type="number"
                            min="0"
                            step="1"
                            value={setDraft.actualDose}
                            disabled={!setDraft.performed}
                            onChange={(event) => updateSet(
                              draft.prescriptionId,
                              setDraft.setIndex,
                              { actualDose: Number(event.target.value) },
                            )}
                          />
                        </label>
                        <label>
                          Set RPE
                          <input
                            type="number"
                            min="0"
                            max="10"
                            step="0.5"
                            value={setDraft.effortRpe ?? ""}
                            disabled={!setDraft.performed}
                            onChange={(event) => updateSet(
                              draft.prescriptionId,
                              setDraft.setIndex,
                              { effortRpe: parseOptionalRpe(event.target.value) },
                            )}
                          />
                        </label>
                        <label>
                          Technique target
                          <select
                            value={setDraft.techniqueConstraintMet === null
                              ? ""
                              : String(setDraft.techniqueConstraintMet)}
                            disabled={!setDraft.performed}
                            onChange={(event) => updateSet(
                              draft.prescriptionId,
                              setDraft.setIndex,
                              {
                                techniqueConstraintMet: event.target.value === ""
                                  ? null
                                  : event.target.value === "true",
                              },
                            )}
                          >
                            <option value="">Not reported</option>
                            <option value="true">Met</option>
                            <option value="false">Not met</option>
                          </select>
                        </label>
                        {setDraft.setIndex < prescription.sets ? (
                          <RestTimer
                            restSeconds={prescription.rest_seconds}
                            enabled={setDraft.performed && workout.phase === "active"}
                          />
                        ) : null}
                      </section>
                    ))}
                  </div>
                  <label>
                    Overall exercise RPE
                    <input
                      type="number"
                      min="0"
                      max="10"
                      step="0.5"
                      value={draft.itemRpe ?? ""}
                      disabled={draft.sets.every((setDraft) => !setDraft.performed)}
                      onChange={(event) => updateItemRpe(
                        draft.prescriptionId,
                        parseOptionalRpe(event.target.value),
                      )}
                    />
                  </label>
                </section>
              );
            })}
          </div>
          {workout.phase === "active" ? (
            <div className="workout-controls">
              <button type="button" onClick={finishWorkout}>Finish workout</button>
              <span>Your set log is saved locally as you go.</span>
            </div>
          ) : !allNotStarted ? (
            <div className="compact-fields time-fields">
              <label>Actual start<input required type="datetime-local" step="1" min={minimumStart} value={workout.startedAt} onChange={(event) => updateWorkout((current) => ({ ...current, startedAt: event.target.value }))} /></label>
              <label>Actual end<input required type="datetime-local" step="1" min={workout.startedAt || minimumStart} value={workout.endedAt} onChange={(event) => updateWorkout((current) => ({ ...current, endedAt: event.target.value }))} /></label>
              <label>Session RPE<input type="number" min="0" max="10" step="0.5" value={workout.sessionRpe} onChange={(event) => updateWorkout((current) => ({ ...current, sessionRpe: event.target.value }))} /></label>
            </div>
          ) : workout.phase === "review" ? (
            <p className="form-help">All exercises are marked not started; no workout times or effort will be recorded.</p>
          ) : null}
          {workout.phase === "review" ? (
            <>
              <label>Workout note <span>(optional)</span><textarea value={workout.note} onChange={(event) => updateWorkout((current) => ({ ...current, note: event.target.value }))} rows={2} /></label>
              <label>Report confidence<select value={workout.reliability} onChange={(event) => updateWorkout((current) => ({ ...current, reliability: event.target.value as Confidence }))}>{confidenceOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
              <div className="workout-controls">
                <button type="submit" disabled={state === "saving"}>{state === "saving" ? "Saving…" : "Save final workout record"}</button>
                <button type="button" className="secondary-button" onClick={() => updateWorkout((current) => ({ ...current, phase: "active", endedAt: "" }))}>Return to set log</button>
              </div>
            </>
          ) : null}
          {message ? <p className="form-error" role="alert">{message}</p> : null}
        </fieldset>
      </form>
      )}
    </details>
  );
}

export function PostSessionSafetyForm({
  apiBaseUrl,
  weeklyPlanId,
  session,
  onSaved,
}: {
  apiBaseUrl: string;
  weeklyPlanId: string;
  session: PlannedSessionProjection;
  onSaved: () => Promise<void>;
}) {
  const execution = session.execution!;
  const [unusualSoreness, setUnusualSoreness] = useState(false);
  const [concerningSymptom, setConcerningSymptom] = useState(false);
  const [note, setNote] = useState("");
  const [reliability, setReliability] = useState<Confidence>("moderate");
  const [state, setState] = useState<"idle" | "saving" | "error">("idle");
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (concerningSymptom) return;
    setState("saving");
    setMessage("");
    const reportedAt = new Date();
    try {
      await submitSafetyCheck(apiBaseUrl, weeklyPlanId, session.planned_session_id, {
        timing: "post_session",
        related_session_execution_id: execution.execution_id,
        readiness: null,
        unusual_soreness: unusualSoreness,
        major_sleep_disruption: false,
        major_schedule_limitation: false,
        signals: [],
        note: note.trim() || null,
        reported_at: reportedAt.toISOString(),
        decided_at: reportedAt.toISOString(),
        reliability,
        provenance: pwaProvenance,
      });
      await onSaved();
      setState("idle");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save the recovery report.");
      setState("error");
    }
  }

  return (
    <details className="action-panel" open>
      <summary>Close out this workout</summary>
      <form className="action-form" onSubmit={submit}>
        <fieldset disabled={state === "saving"}>
          <legend>Anything unusual after the session?</legend>
          <div className="check-list">
            <label>
              <input
                type="checkbox"
                checked={unusualSoreness}
                onChange={(event) => setUnusualSoreness(event.target.checked)}
              />
              Unusual soreness after this workout
            </label>
            <label>
              <input
                type="checkbox"
                checked={concerningSymptom}
                onChange={(event) => setConcerningSymptom(event.target.checked)}
              />
              Pain or another concerning symptom requiring assessment
            </label>
          </div>
          {concerningSymptom ? (
            <p className="safety-stop" role="alert">
              Normal progression is paused. This prototype cannot classify symptoms or provide
              medical guidance. Seek appropriate evaluation when a symptom is concerning.
            </p>
          ) : null}
          <label>
            Recovery note <span>(optional)</span>
            <textarea value={note} onChange={(event) => setNote(event.target.value)} rows={2} />
          </label>
          <label>
            Report confidence
            <select
              value={reliability}
              onChange={(event) => setReliability(event.target.value as Confidence)}
            >
              {confidenceOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={concerningSymptom || state === "saving"}>
            {state === "saving" ? "Closing…" : "Save recovery report"}
          </button>
          {message ? <p className="form-error" role="alert">{message}</p> : null}
        </fieldset>
      </form>
    </details>
  );
}

export function ProgressionEvaluationButton({
  apiBaseUrl,
  executionId,
  prescriptionId,
  onSaved,
}: {
  apiBaseUrl: string;
  executionId: string;
  prescriptionId: string;
  onSaved: () => Promise<void>;
}) {
  const [state, setState] = useState<"idle" | "saving" | "error">("idle");
  const [message, setMessage] = useState("");

  async function evaluate() {
    setState("saving");
    setMessage("");
    try {
      const command = buildProgressionEvaluationCommand();
      await submitProgressionEvaluation(
        apiBaseUrl,
        executionId,
        prescriptionId,
        command,
      );
      await onSaved();
      setState("idle");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to evaluate progression.");
      setState("error");
    }
  }

  return (
    <div className="progression-action">
      <button type="button" disabled={state === "saving"} onClick={() => void evaluate()}>
        {state === "saving" ? "Evaluating…" : "Evaluate progression"}
      </button>
      {message ? <p className="form-error" role="alert">{message}</p> : null}
    </div>
  );
}
