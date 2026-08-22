"use client";

import { FormEvent, useMemo, useState } from "react";

import {
  buildExecutionCommand,
  pwaProvenance,
  submitSafetyCheck,
  submitSessionExecution,
  type Confidence,
  type PlannedSessionProjection,
  type PrescriptionLogDraft,
} from "@/lib/current-week";

const confidenceOptions: Array<{ value: Confidence; label: string }> = [
  { value: "moderate", label: "Moderate confidence" },
  { value: "high", label: "High confidence" },
  { value: "low", label: "Low confidence" },
  { value: "unknown", label: "Unknown confidence" },
];

function localDateTime(value: string): string {
  const source = new Date(value);
  const date = new Date(Math.ceil(source.getTime() / 60_000) * 60_000);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function parseOptionalRpe(value: string): number | null {
  return value === "" ? null : Number(value);
}

export function SafetyCheckForm({
  apiBaseUrl,
  weeklyPlanId,
  safetyPolicyId,
  session,
  onSaved,
}: {
  apiBaseUrl: string;
  weeklyPlanId: string;
  safetyPolicyId: string;
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
        safety_policy_id: safetyPolicyId,
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
  const initialDrafts = useMemo<PrescriptionLogDraft[]>(
    () => session.prescriptions.map((prescription) => ({
      prescriptionId: prescription.prescription_id,
      performedSets: prescription.sets,
      actualDosePerSet: prescription.repetitions_per_set ?? prescription.duration_seconds ?? 0,
      itemRpe: null,
    })),
    [session.prescriptions],
  );
  const [drafts, setDrafts] = useState(initialDrafts);
  const [startedAt, setStartedAt] = useState("");
  const [endedAt, setEndedAt] = useState("");
  const [sessionRpe, setSessionRpe] = useState("");
  const [note, setNote] = useState("");
  const [reliability, setReliability] = useState<Confidence>("moderate");
  const [state, setState] = useState<"idle" | "saving" | "error">("idle");
  const [message, setMessage] = useState("");
  const allNotStarted = drafts.every((draft) => draft.performedSets === 0);

  function updateDraft(prescriptionId: string, update: Partial<PrescriptionLogDraft>) {
    setDrafts((current) => current.map((draft) => draft.prescriptionId === prescriptionId ? { ...draft, ...update } : draft));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("saving");
    setMessage("");
    try {
      const command = buildExecutionCommand({
        session,
        drafts,
        safetyDecisionId: safety.decision_id,
        requiredModifications: safety.required_modifications,
        startedAt: allNotStarted ? null : new Date(startedAt),
        endedAt: allNotStarted ? null : new Date(endedAt),
        sessionRpe: parseOptionalRpe(sessionRpe),
        note,
        reliability,
      });
      await submitSessionExecution(apiBaseUrl, weeklyPlanId, session.planned_session_id, command);
      await onSaved();
      setState("idle");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save the workout log.");
      setState("error");
    }
  }

  const minimumStart = localDateTime(safety.decided_at);
  return (
    <details className="action-panel">
      <summary>Log workout result</summary>
      <form className="action-form" onSubmit={submit}>
        <fieldset disabled={state === "saving"}>
          <legend>What did you actually complete?</legend>
          <p className="form-help">Prescribed values are prefilled for review. Change them before saving if the workout differed.</p>
          <div className="execution-items">
            {session.prescriptions.map((prescription, index) => {
              const draft = drafts[index];
              const unit = prescription.repetitions_per_set === null ? "seconds per set" : "reps per set";
              return (
                <section key={prescription.prescription_id} className="execution-item">
                  <strong>{prescription.exercise_name}</strong>
                  <div className="compact-fields">
                    <label>Sets completed<input type="number" min="0" max={prescription.sets} step="1" value={draft.performedSets} onChange={(event) => updateDraft(draft.prescriptionId, { performedSets: Number(event.target.value) })} /></label>
                    <label>{unit}<input type="number" min="0" step="1" value={draft.actualDosePerSet} disabled={draft.performedSets === 0} onChange={(event) => updateDraft(draft.prescriptionId, { actualDosePerSet: Number(event.target.value) })} /></label>
                    <label>Item RPE<input type="number" min="0" max="10" step="0.5" value={draft.itemRpe ?? ""} disabled={draft.performedSets === 0} onChange={(event) => updateDraft(draft.prescriptionId, { itemRpe: parseOptionalRpe(event.target.value) })} /></label>
                  </div>
                </section>
              );
            })}
          </div>
          {!allNotStarted ? (
            <div className="compact-fields time-fields">
              <label>Actual start<input required type="datetime-local" min={minimumStart} value={startedAt} onChange={(event) => setStartedAt(event.target.value)} /></label>
              <label>Actual end<input required type="datetime-local" min={startedAt || minimumStart} value={endedAt} onChange={(event) => setEndedAt(event.target.value)} /></label>
              <label>Session RPE<input type="number" min="0" max="10" step="0.5" value={sessionRpe} onChange={(event) => setSessionRpe(event.target.value)} /></label>
            </div>
          ) : (
            <p className="form-help">All exercises are marked not started; no workout times or effort will be recorded.</p>
          )}
          <label>Workout note <span>(optional)</span><textarea value={note} onChange={(event) => setNote(event.target.value)} rows={2} /></label>
          <label>Report confidence<select value={reliability} onChange={(event) => setReliability(event.target.value as Confidence)}>{confidenceOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
          <button type="submit" disabled={state === "saving"}>{state === "saving" ? "Saving…" : "Save workout result"}</button>
          {message ? <p className="form-error" role="alert">{message}</p> : null}
        </fieldset>
      </form>
    </details>
  );
}

export function PostSessionSafetyForm({
  apiBaseUrl,
  weeklyPlanId,
  safetyPolicyId,
  session,
  onSaved,
}: {
  apiBaseUrl: string;
  weeklyPlanId: string;
  safetyPolicyId: string;
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
        safety_policy_id: safetyPolicyId,
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
