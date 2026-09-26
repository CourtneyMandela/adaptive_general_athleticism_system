"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  buildAssessmentAttemptCommand,
  buildAssessmentResultCommand,
  buildAssessmentReadinessReportCommand,
  buildAssessmentRunCommand,
  buildIntroductoryExposureExecutionCommand,
  fetchAssessmentWorkflow,
  submitAssessmentCapabilityEstimate,
  submitAssessmentAttempt,
  submitAssessmentReadinessReport,
  submitAssessmentResult,
  submitAssessmentRun,
  submitIntroductoryExposureExecution,
  type AssessmentDecisionProjection,
  type AssessmentAttemptReason,
  type AssessmentAttemptStatus,
  type AssessmentHistoryRunProjection,
  type AssessmentWorkflowProjection,
  type ReadinessAnswer,
} from "@/lib/assessment";
import type { Confidence } from "@/lib/current-week";

const capabilityDomains = [
  ["aerobic_capacity", "Aerobic capacity"],
  ["maximal_strength", "Maximal strength"],
  ["explosive_power", "Explosive power"],
  ["muscular_endurance", "Muscular endurance"],
  ["speed", "Speed"],
  ["change_of_direction", "Change of direction"],
  ["mobility", "Mobility"],
  ["balance_control", "Balance and control"],
  ["loaded_locomotion", "Loaded locomotion"],
] as const;

function splitTags(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function displayValue(value: unknown): string {
  return typeof value === "string" || typeof value === "number"
    ? String(value)
    : JSON.stringify(value);
}

function statusLabel(status: string): string {
  return status.replaceAll("_", " ");
}

const readinessAnswerOptions = [
  ["unsure", "I’m not sure"],
  ["no", "No"],
  ["yes", "Yes"],
] as const;

function AssessmentAttemptHistory({
  attempts,
}: {
  attempts: AssessmentDecisionProjection["attempts"];
}) {
  if (!attempts.length) return null;
  return (
    <section className="assessment-attempt-history" aria-label="Recorded incomplete attempts">
      <strong>Incomplete attempt history</strong>
      <ul>
        {attempts.map((attempt) => (
          <li key={attempt.attempt_id}>
            <span>{statusLabel(attempt.status)}</span>
            <time dateTime={attempt.attempted_at}>
              {new Date(attempt.attempted_at).toLocaleString()}
            </time>
            <small>
              Reason: {statusLabel(attempt.reason)} · Not eligible for capability estimation
            </small>
          </li>
        ))}
      </ul>
    </section>
  );
}

function AssessmentLongitudinalHistory({
  runs,
}: {
  runs: AssessmentHistoryRunProjection[];
}) {
  if (!runs.length) return null;
  return (
    <details className="assessment-longitudinal-history">
      <summary>Assessment history across {runs.length} selection run{runs.length === 1 ? "" : "s"}</summary>
      <p className="form-help">
        Incomplete attempts, completed direct observations, and derived capability estimates remain
        separate records. Newer records do not overwrite earlier runs.
      </p>
      <div className="assessment-history-runs">
        {runs.map((run) => (
          <article key={run.run_id} className="assessment-history-run">
            <header>
              <strong>{run.environment_name}</strong>
              <time dateTime={run.evaluated_at}>{new Date(run.evaluated_at).toLocaleString()}</time>
            </header>
            {run.selections.map((selection) => (
              <section key={selection.selection_id} className="assessment-history-selection">
                <div>
                  <strong>{selection.name}</strong>
                  <span className={`status-badge status-badge--${selection.decision}`}>
                    {statusLabel(selection.decision)}
                  </span>
                </div>
                <p>{statusLabel(selection.domain)} · protocol {selection.protocol_version}</p>
                <AssessmentAttemptHistory attempts={selection.attempts} />
                {selection.completed_result ? (
                  <div className="assessment-history-result">
                    <p>
                      <strong>Completed direct observation:</strong>{" "}
                      {displayValue(selection.completed_result.measurement)}{" "}
                      {selection.completed_result.unit ?? ""} · {selection.completed_result.reliability}
                      {" "}reliability
                    </p>
                    <p className="form-help">
                      Protocol completion{" "}
                      {selection.completed_result.protocol_completion_attested
                        ? "attested"
                        : "not historically attested"}
                      {" · "}no-stop condition{" "}
                      {selection.completed_result.no_stop_condition_attested
                        ? "attested"
                        : "not historically attested"}
                    </p>
                    {selection.completed_result.capability_estimates.length ? (
                      <ul className="assessment-history-estimates">
                        {selection.completed_result.capability_estimates.map((estimate) => (
                          <li key={estimate.estimate_id}>
                            <strong>Derived estimate:</strong> {displayValue(estimate.estimate)}{" "}
                            {estimate.unit_or_scale} · {estimate.confidence} confidence ·{" "}
                            {estimate.valid_as_of ? "current at this view" : "not current"}
                            <small>
                              Method {estimate.calculation_method} · {estimate.source_observation_ids.length}
                              {" "}source observation(s) · policy {estimate.policy_id}
                            </small>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="form-help">No derived capability estimate is linked to this result.</p>
                    )}
                  </div>
                ) : selection.attempts.length === 0 ? (
                  <p className="form-help">No attempt or completed result was recorded.</p>
                ) : null}
                <details>
                  <summary>Historical lineage</summary>
                  <p className="form-help">
                    Run {run.run_id} · selection {selection.selection_id} · context observation{" "}
                    {run.context_observation_id} · eligibility review{" "}
                    {selection.assessment_eligibility_review_id ?? run.assessment_eligibility_review_id}
                  </p>
                  <p className="form-help">
                    Selection rule {selection.rule_version} · run rule {run.rule_version} · review{" "}
                    {selection.review_version ?? "not attached"}
                  </p>
                </details>
              </section>
            ))}
          </article>
        ))}
      </div>
    </details>
  );
}

function ReadinessSelect({
  label,
  help,
  value,
  onChange,
}: {
  label: string;
  help?: string;
  value: ReadinessAnswer;
  onChange: (value: ReadinessAnswer) => void;
}) {
  return (
    <label>
      {label}
      {help ? <span>{help}</span> : null}
      <select value={value} onChange={(event) => onChange(event.target.value as ReadinessAnswer)}>
        {readinessAnswerOptions.map(([option, text]) => (
          <option value={option} key={option}>{text}</option>
        ))}
      </select>
    </label>
  );
}

function AssessmentResultForm({
  apiBaseUrl,
  athleteId,
  runId,
  decision,
  onSaved,
}: {
  apiBaseUrl: string;
  athleteId: string;
  runId: string;
  decision: AssessmentDecisionProjection;
  onSaved: () => Promise<void>;
}) {
  const schema = decision.measurement_schema;
  const [value, setValue] = useState(
    schema?.measurement_type === "category" ? (schema.allowed_values[0] ?? "") : "",
  );
  const [reliability, setReliability] = useState<Confidence>("moderate");
  const [outcome, setOutcome] = useState<"" | "completed" | AssessmentAttemptStatus>("");
  const [attemptReason, setAttemptReason] = useState<
    "" | Exclude<AssessmentAttemptReason, "legacy_unspecified">
  >("");
  const [state, setState] = useState<"idle" | "saving" | "error">("idle");
  const [message, setMessage] = useState("");

  if (!schema) {
    return null;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("saving");
    setMessage("");
    try {
      if (outcome === "completed") {
        const command = buildAssessmentResultCommand(decision, value, reliability, {
          protocolCompleted: true,
          stopConditionOccurred: false,
        });
        await submitAssessmentResult(
          apiBaseUrl,
          athleteId,
          runId,
          decision.selection_id,
          command,
        );
      } else if (outcome === "incomplete" || outcome === "safety_stopped") {
        const reason = outcome === "safety_stopped" ? "listed_stop_condition" : attemptReason;
        if (!reason) {
          throw new Error("Choose the non-safety reason this attempt was incomplete.");
        }
        const command = buildAssessmentAttemptCommand(outcome, reason, reliability);
        await submitAssessmentAttempt(
          apiBaseUrl,
          athleteId,
          runId,
          decision.selection_id,
          command,
        );
      } else {
        throw new Error("Choose how this assessment attempt ended.");
      }
      await onSaved();
      setOutcome("");
      setAttemptReason("");
      setState("idle");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to record this result.");
      setState("error");
    }
  }

  return (
    <form className="assessment-result-form" onSubmit={submit}>
      <fieldset className="assessment-protocol-confirmation">
        <legend>Complete the exact reviewed protocol before recording a result</legend>
        <ol className="protocol-steps">
          {decision.protocol_instructions.map((instruction) => (
            <li key={instruction}>{instruction}</li>
          ))}
        </ol>
        <p><strong>Result entry:</strong> {decision.result_entry_instructions}</p>
        <label>
          <input
            type="radio"
            name={`assessment-outcome-${decision.selection_id}`}
            value="completed"
            checked={outcome === "completed"}
            onChange={() => {
              setOutcome("completed");
              setAttemptReason("");
            }}
          />
          I completed the exact reviewed protocol without a stop condition, and this is the direct
          result from that completed attempt.
        </label>
        <label>
          <input
            type="radio"
            name={`assessment-outcome-${decision.selection_id}`}
            value="incomplete"
            checked={outcome === "incomplete"}
            onChange={() => {
              setOutcome("incomplete");
              setAttemptReason("");
            }}
          />
          I did not complete the protocol, but no listed stop condition occurred.
        </label>
        <label>
          <input
            type="radio"
            name={`assessment-outcome-${decision.selection_id}`}
            value="safety_stopped"
            checked={outcome === "safety_stopped"}
            onChange={() => {
              setOutcome("safety_stopped");
              setAttemptReason("listed_stop_condition");
            }}
          />
          I stopped because a listed stop condition occurred.
        </label>
        {outcome === "safety_stopped" ? (
          <aside className="review-boundary">
            <strong>Do not record this as a completed assessment.</strong>
            <span>
              A stopped attempt is not a zero result. AGAS will preserve the stop as an attempt that
              cannot become a capability estimate. Update your readiness report if your current
              state changed and seek appropriate guidance for concerning symptoms.
            </span>
          </aside>
        ) : null}
        {outcome === "incomplete" ? (
          <label>
            Why was the protocol incomplete?
            <span>
              Choose a factual non-safety reason. Do not enter a partial result or symptom narrative.
            </span>
            <select
              required
              value={attemptReason}
              onChange={(event) => setAttemptReason(
                event.target.value as Exclude<AssessmentAttemptReason, "legacy_unspecified">,
              )}
            >
              <option value="">Choose a reason</option>
              <option value="setup_or_equipment_issue">Setup or equipment issue</option>
              <option value="measurement_or_route_issue">Measurement or route issue</option>
              <option value="instructions_unclear">Instructions were unclear</option>
              <option value="external_interruption">External interruption</option>
              <option value="voluntary_non_safety_stop">Chose to stop for a non-safety reason</option>
              <option value="other_non_safety_reason">Another non-safety reason</option>
            </select>
          </label>
        ) : null}
      </fieldset>
      <label>
        {schema.label}
        {schema.measurement_type === "category" ? (
          <select
            value={value}
            disabled={outcome === "incomplete" || outcome === "safety_stopped"}
            onChange={(event) => setValue(event.target.value)}
          >
            {schema.allowed_values.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        ) : (
          <input
            type="number"
            required={outcome === "completed"}
            disabled={outcome === "incomplete" || outcome === "safety_stopped"}
            min={schema.minimum ?? undefined}
            max={schema.maximum ?? undefined}
            step={schema.step ?? (schema.measurement_type === "integer" ? 1 : "any")}
            value={value}
            onChange={(event) => setValue(event.target.value)}
          />
        )}
      </label>
      <span className="assessment-unit">{decision.unit_or_scale}</span>
      <label>
        Report reliability
        <select value={reliability} onChange={(event) => setReliability(event.target.value as Confidence)}>
          <option value="moderate">Reasonably certain</option>
          <option value="high">Very certain</option>
          <option value="low">Some uncertainty</option>
          <option value="unknown">Unknown</option>
        </select>
      </label>
      <button
        type="submit"
        disabled={
          state === "saving" || outcome === "" || (outcome === "incomplete" && !attemptReason)
        }
      >
        {state === "saving"
          ? "Recording…"
          : outcome === "completed"
            ? "Record result observation"
            : "Record incomplete attempt"}
      </button>
      <p className="form-help">
        Schema {schema.measurement_schema_version}. Recording does not create or display a capability
        score.
      </p>
      {message ? <p className="form-error" role="alert">{message}</p> : null}
    </form>
  );
}

export function AssessmentPanel({
  apiBaseUrl,
  athleteId,
  onChanged,
}: {
  apiBaseUrl: string;
  athleteId: string;
  onChanged: () => Promise<void>;
}) {
  const [workflow, setWorkflow] = useState<AssessmentWorkflowProjection | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "saving" | "error">("loading");
  const [message, setMessage] = useState("");
  const [environmentId, setEnvironmentId] = useState("");
  const [bodyMass, setBodyMass] = useState("");
  const [skills, setSkills] = useState("");
  const [exposures, setExposures] = useState("");
  const [trainingHistory, setTrainingHistory] = useState<Record<string, string>>({});
  const [reliability, setReliability] = useState<Confidence>("moderate");
  const [adultConfirmed, setAdultConfirmed] = useState(false);
  const [activity, setActivity] = useState<ReadinessAnswer>("unsure");
  const [knownDisease, setKnownDisease] = useState<ReadinessAnswer>("unsure");
  const [symptoms, setSymptoms] = useState<ReadinessAnswer>("unsure");
  const [restriction, setRestriction] = useState<ReadinessAnswer>("unsure");
  const [movementConcern, setMovementConcern] = useState<ReadinessAnswer>("unsure");
  const [controlledRepetition, setControlledRepetition] = useState<ReadinessAnswer>("unsure");
  const [upperBodyConcern, setUpperBodyConcern] = useState<ReadinessAnswer>("unsure");
  const [controlledPushup, setControlledPushup] = useState<ReadinessAnswer>("unsure");
  const [controlledJumpLanding, setControlledJumpLanding] = useState<ReadinessAnswer>("unsure");
  const [recentJumpExposure, setRecentJumpExposure] = useState<ReadinessAnswer>("unsure");
  const [readinessConfirmed, setReadinessConfirmed] = useState(false);
  const [readinessAction, setReadinessAction] = useState("");
  const [exposureStartedAt, setExposureStartedAt] = useState<Date | null>(null);
  const [exposurePreReady, setExposurePreReady] = useState(false);
  const [exposureSets, setExposureSets] = useState("2");
  const [exposureContacts, setExposureContacts] = useState("6");
  const [exposureRpe, setExposureRpe] = useState("");
  const [controlledLandings, setControlledLandings] = useState(false);
  const [stopCondition, setStopCondition] = useState(false);
  const [exposureConfirmed, setExposureConfirmed] = useState(false);
  const [exposureAction, setExposureAction] = useState("");

  async function load() {
    setState("loading");
    setMessage("");
    try {
      const result = await fetchAssessmentWorkflow(apiBaseUrl, athleteId);
      setWorkflow(result);
      setEnvironmentId((current) => current || result.environments[0]?.environment_id || "");
      setState("ready");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load assessment status.");
      setState("error");
    }
  }

  useEffect(() => {
    let active = true;
    void fetchAssessmentWorkflow(apiBaseUrl, athleteId)
      .then((result) => {
        if (active) {
          setWorkflow(result);
          setEnvironmentId(result.environments[0]?.environment_id ?? "");
          setMessage("");
          setState("ready");
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(error instanceof Error ? error.message : "Unable to load assessment status.");
          setState("error");
        }
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl, athleteId]);

  async function startRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("saving");
    setMessage("");
    try {
      const command = buildAssessmentRunCommand({
        environmentId,
        bodyMassKg: bodyMass ? Number(bodyMass) : null,
        trainingAgeMonthsByDomain: Object.fromEntries(
          capabilityDomains.map(([domain]) => [
            domain,
            trainingHistory[domain] ? Number(trainingHistory[domain]) : null,
          ]),
        ),
        exerciseSkillTags: splitTags(skills),
        recentExposureTags: splitTags(exposures),
        reliability,
      });
      await submitAssessmentRun(apiBaseUrl, athleteId, command);
      await load();
      await onChanged();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to start assessment selection.");
      setState("error");
    }
  }

  async function submitReadiness(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("saving");
    setMessage("");
    setReadinessAction("");
    try {
      const result = await submitAssessmentReadinessReport(
        apiBaseUrl,
        athleteId,
        buildAssessmentReadinessReportCommand({
          adultConfirmed,
          regularModerateActivityLastThreeMonths: activity,
          knownCardiovascularMetabolicOrRenalDisease: knownDisease,
          concerningSignsOrSymptoms: symptoms,
          clinicianExerciseRestriction: restriction,
          currentLowerBodyOrBalanceConcern: movementConcern,
          controlledChairStandWithoutArms: controlledRepetition,
          currentUpperBodyWristOrHandConcern: upperBodyConcern,
          controlledStandardPushup: controlledPushup,
          controlledTwoFootJumpAndLanding: controlledJumpLanding,
          recentTwoFootJumpAndLandingExposure28Days: recentJumpExposure,
          answersConfirmed: readinessConfirmed,
        }),
      );
      setReadinessAction(`${result.next_action} ${result.jump_exposure_next_action}`);
      await load();
      await onChanged();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save readiness.");
      setState("error");
    }
  }

  async function createCapabilityEstimate(performanceId: string) {
    setState("saving");
    setMessage("");
    try {
      await submitAssessmentCapabilityEstimate(apiBaseUrl, athleteId, performanceId);
      await load();
      await onChanged();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Unable to create the capability estimate.",
      );
      setState("error");
    }
  }

  async function recordIntroductoryExposure(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workflow?.jump_exposure_need || !exposureStartedAt) {
      setMessage("Start the exposure timer before recording the session.");
      return;
    }
    setState("saving");
    setMessage("");
    setExposureAction("");
    try {
      const result = await submitIntroductoryExposureExecution(
        apiBaseUrl,
        athleteId,
        buildIntroductoryExposureExecutionCommand({
          exposureNeedId: workflow.jump_exposure_need.exposure_need_id,
          environmentId,
          startedAt: exposureStartedAt,
          endedAt: new Date(),
          actualSets: Number(exposureSets),
          actualContacts: Number(exposureContacts),
          sessionRpe: exposureRpe ? Number(exposureRpe) : null,
          preSessionReady: exposurePreReady,
          controlledLandings,
          stopConditionOccurred: stopCondition,
          answersConfirmed: exposureConfirmed,
          reliability: "moderate",
        }),
      ) as { next_action?: string };
      setExposureAction(result.next_action ?? "Exposure record saved.");
      setExposureStartedAt(null);
      setExposurePreReady(false);
      setExposureConfirmed(false);
      setControlledLandings(false);
      setStopCondition(false);
      setExposureRpe("");
      await load();
      await onChanged();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to record the exposure.");
      setState("error");
    }
  }

  return (
    <section className="assessment-panel" aria-labelledby="assessment-title">
      <header className="assessment-panel__heading">
        <div>
          <p className="eyebrow">Assessment</p>
          <h2 id="assessment-title">Measure first. Interpret later.</h2>
        </div>
        {workflow ? (
          <span className={`status-badge status-badge--${workflow.status}`}>
            {statusLabel(workflow.status)}
          </span>
        ) : null}
      </header>

      {state === "loading" ? <p className="form-help">Loading governed assessment state…</p> : null}
      {workflow ? <p className="assessment-message">{workflow.message}</p> : null}
      {message ? <p className="form-error" role="alert">{message}</p> : null}

      {workflow ? (
        <dl className="assessment-summary">
          <div>
            <dt>Eligibility</dt>
            <dd>
              {workflow.eligibility
                ? `${statusLabel(workflow.eligibility.outcome)} until ${new Date(
                    workflow.eligibility.valid_until,
                  ).toLocaleString()} · up to ${statusLabel(
                    workflow.eligibility.maximum_assessment_intensity,
                  )} intensity`
                : "Current readiness check required"}
            </dd>
          </div>
          <div>
            <dt>Evidence-ready self-administered protocols</dt>
            <dd>{workflow.approved_self_administered_protocol_count}</dd>
          </div>
          <div>
            <dt>Reassessment</dt>
            <dd>
              {workflow.due_protocol_count
                ? `${workflow.due_protocol_count} due now`
                : workflow.next_reassessment_at
                  ? `Next ${new Date(workflow.next_reassessment_at).toLocaleDateString()}`
                  : "No current due date"}
            </dd>
          </div>
          {workflow.jump_exposure_need ? (
            <div>
              <dt>Maximal jump assessment exposure</dt>
              <dd>
                {workflow.jump_exposure_need.status === "recent_exposure_confirmed"
                  ? "Recent exposure reported"
                  : workflow.jump_exposure_need.status === "introductory_exposure_needed"
                    ? "Introductory jump-and-landing exposure needed"
                    : "Recent exposure not confirmed"}
                {workflow.jump_exposure_need.active ? "" : " · report expired"}
              </dd>
            </div>
          ) : null}
        </dl>
      ) : null}
      <AssessmentLongitudinalHistory runs={workflow?.history_runs ?? []} />
      {workflow?.jump_exposure_need?.status === "introductory_exposure_needed" ? (
        <aside className="review-boundary">
          {workflow.introductory_jump_dose ? (
            <>
              <strong>Your introductory jump dose is ready to perform and log.</strong>
              <span>
                {workflow.introductory_jump_dose.exercise_name}: {workflow.introductory_jump_dose.sets}
                {" × "}{workflow.introductory_jump_dose.repetitions_per_set} easy, separately reset
                repetitions ({workflow.introductory_jump_dose.total_contacts} contacts total), with
                {" "}{workflow.introductory_jump_dose.rest_seconds} seconds rest. Keep effort at RPE
                {" "}{workflow.introductory_jump_dose.effort_rpe_minimum}–
                {workflow.introductory_jump_dose.effort_rpe_maximum}.
              </span>
              <span>
                This is a provisional engineering starting dose, not clearance for maximal jumping.
                It counts only when you complete the exact easy dose with controlled landings at or
                below the RPE cap. You need {workflow.introductory_jump_history?.required_days ?? 2}
                {" "}qualifying days; {workflow.introductory_jump_history?.qualifying_days ?? 0}
                {" "}are currently logged.
              </span>
              <form className="assessment-form" onSubmit={recordIntroductoryExposure}>
                <label>
                  Training environment
                  <select
                    required
                    value={environmentId}
                    onChange={(event) => setEnvironmentId(event.target.value)}
                  >
                    {workflow.environments.map((environment) => (
                      <option key={environment.environment_id} value={environment.environment_id}>
                        {environment.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={exposurePreReady}
                    onChange={(event) => setExposurePreReady(event.target.checked)}
                  />
                  Right now I have no pain, dizziness, instability, unusual symptoms, or other
                  reason to avoid these easy jumps, and my readiness answers are still current.
                </label>
                {!exposureStartedAt ? (
                  <button
                    type="button"
                    disabled={
                      !exposurePreReady ||
                      !environmentId ||
                      workflow.introductory_jump_history?.session_recorded_today
                    }
                    onClick={() => {
                      setExposureSets(String(workflow.introductory_jump_dose?.sets ?? 2));
                      setExposureContacts(
                        String(workflow.introductory_jump_dose?.total_contacts ?? 6),
                      );
                      setExposureStartedAt(new Date());
                    }}
                  >
                    {workflow.introductory_jump_history?.session_recorded_today
                      ? "One session already recorded today"
                      : "Start this exposure"}
                  </button>
                ) : (
                  <>
                    <ol className="protocol-steps">
                      {workflow.introductory_jump_dose.technique_constraints.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ol>
                    <p className="form-help">
                      Started {exposureStartedAt.toLocaleTimeString()}. Complete 3 easy contacts,
                      rest 90 seconds, then complete 3 more. Stop immediately if any listed stop
                      condition occurs.
                    </p>
                    <label>
                      Sets actually completed
                      <input
                        type="number"
                        min="0"
                        step="1"
                        required
                        value={exposureSets}
                        onChange={(event) => setExposureSets(event.target.value)}
                      />
                    </label>
                    <label>
                      Jump contacts actually completed
                      <input
                        type="number"
                        min="0"
                        step="1"
                        required
                        value={exposureContacts}
                        onChange={(event) => setExposureContacts(event.target.value)}
                      />
                    </label>
                    <label>
                      Overall effort (RPE 0–10)
                      <input
                        type="number"
                        min="0"
                        max="10"
                        step="0.5"
                        required
                        value={exposureRpe}
                        onChange={(event) => setExposureRpe(event.target.value)}
                      />
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={controlledLandings}
                        onChange={(event) => setControlledLandings(event.target.checked)}
                      />
                      Every completed landing was controlled and separately reset.
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={stopCondition}
                        onChange={(event) => setStopCondition(event.target.checked)}
                      />
                      A stop condition occurred (pain, dizziness, instability, uncontrolled
                      landing, unusual symptoms, or inability to keep the effort easy).
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={exposureConfirmed}
                        onChange={(event) => setExposureConfirmed(event.target.checked)}
                      />
                      This record accurately describes what I performed. I understand a partial
                      or safety-stopped session is preserved but does not count as a qualifying day.
                    </label>
                    <button type="submit" disabled={state === "saving"}>
                      {state === "saving" ? "Saving…" : "Finish and save exposure"}
                    </button>
                  </>
                )}
              </form>
            </>
          ) : (
            <>
              <strong>AGAS owes you an introductory jump-and-landing path.</strong>
              <span>
                The maximal jump test stays excluded. This is an exposure prerequisite—not a low
                fitness score—and its reviewed exercise and dose authority are not available yet.
              </span>
            </>
          )}
        </aside>
      ) : null}
      {exposureAction ? <p className="form-success" role="status">{exposureAction}</p> : null}
      {readinessAction ? <p className="form-success" role="status">{readinessAction}</p> : null}

      {workflow && workflow.approved_self_administered_protocol_count > 0 && [
        "eligibility_required",
        "eligibility_review_required",
        "selection_blocked",
        "eligibility_inactive",
      ].includes(workflow.status) ? (
        <details className="assessment-start" open>
          <summary>Complete the current readiness check</summary>
          <form className="assessment-form" onSubmit={submitReadiness}>
            <aside className="review-boundary">
              <strong>This is a stop/go screen, not medical clearance.</strong>
              <span>
                Answer facts only. AGAS does not diagnose a symptom or decide whether a known
                condition is safe; “yes” or “unsure” stops the assessment and asks for qualified
                guidance.
              </span>
            </aside>
            <label>
              <input
                type="checkbox"
                checked={adultConfirmed}
                onChange={(event) => setAdultConfirmed(event.target.checked)}
              />
              I confirm that I am an adult (18 or older).
            </label>
            <ReadinessSelect
              label="For the last 3 months, have you done planned moderate exercise at least 3 days per week for 30 minutes?"
              help="This sets only the maximum assessment-effort ceiling. It is not converted to a fitness score."
              value={activity}
              onChange={setActivity}
            />
            <ReadinessSelect
              label="Has a healthcare professional told you that you have cardiovascular disease, diabetes, or kidney disease?"
              value={knownDisease}
              onChange={setKnownDisease}
            />
            <ReadinessSelect
              label="Do you currently have any concerning signs or symptoms?"
              help="Examples: chest/neck/jaw/arm discomfort; fainting or dizziness; unusual breathlessness at rest, with mild activity, or during usual activities; unexplained ankle swelling; or an unexplained racing/irregular heartbeat."
              value={symptoms}
              onChange={setSymptoms}
            />
            <ReadinessSelect
              label="Has a healthcare professional told you to avoid or limit exercise that would include repeated chair stands, push-ups, or jumping?"
              value={restriction}
              onChange={setRestriction}
            />
            <ReadinessSelect
              label="Do you currently have lower-body pain, an injury, or a balance concern that could affect repeated chair stands or jumping?"
              value={movementConcern}
              onChange={setMovementConcern}
            />
            <ReadinessSelect
              label="Using the exact stable chair setup, can you comfortably stand once and sit with control without using your arms?"
              value={controlledRepetition}
              onChange={setControlledRepetition}
            />
            <ReadinessSelect
              label="Do you currently have upper-body, wrist, or hand pain or an injury that could affect standard push-ups?"
              value={upperBodyConcern}
              onChange={setUpperBodyConcern}
            />
            <ReadinessSelect
              label="On a nonslip floor, can you comfortably complete one controlled standard push-up from toes to straight arms without pain?"
              help="This is only a movement pre-check. It is not the maximum-repetition test."
              value={controlledPushup}
              onChange={setControlledPushup}
            />
            <ReadinessSelect
              label="On a clear nonslip surface, can you comfortably perform one low-effort two-foot jump and land under control without pain, instability, or unusual symptoms?"
              help="This is only a movement pre-check. It is not the maximal jump assessment."
              value={controlledJumpLanding}
              onChange={setControlledJumpLanding}
            />
            <ReadinessSelect
              label="During the last 28 days, have you intentionally practiced two-foot jumping and controlled landing on at least two separate days?"
              help="This is a factual recent-exposure check, not proof that maximal jumping is risk-free. No or unsure excludes only jump assessments."
              value={recentJumpExposure}
              onChange={setRecentJumpExposure}
            />
            <label>
              <input
                type="checkbox"
                checked={readinessConfirmed}
                onChange={(event) => setReadinessConfirmed(event.target.checked)}
              />
              These answers describe my current state and are accurate to the best of my
              knowledge. I understand that AGAS stores these grouped answers in my private
              assessment history.
            </label>
            <button type="submit" disabled={state === "saving" || !readinessConfirmed}>
              {state === "saving" ? "Checking…" : "Evaluate current readiness"}
            </button>
            <p className="form-help">
              A clear result expires after 24 hours and can authorize only evidence-ready
              self-administered assessments up to the server-calculated effort ceiling. Stop if your condition changes.
              This app cannot assess urgency; if you think you may have a medical emergency, use
              local emergency services.
            </p>
          </form>
        </details>
      ) : null}
      {workflow ? (
        <p className="form-help">
          Reassessment cadence {workflow.reassessment_rule_version}; interval values come from
          evidence-ready reviewed protocol history.
        </p>
      ) : null}

      {workflow?.latest_run ? (
        <div className="assessment-decisions">
          <p className="form-help">
            Latest selection · {workflow.latest_run.environment_name} ·{" "}
            {new Date(workflow.latest_run.evaluated_at).toLocaleString()}
          </p>
          {workflow.latest_run.decisions.map((item) => (
            <article className="assessment-decision" key={item.selection_id}>
              <header>
                <div>
                  <h3>{item.name}</h3>
                  <p>{statusLabel(item.domain)} · {item.unit_or_scale}</p>
                </div>
                <span className={`status-badge status-badge--${item.decision}`}>
                  {statusLabel(item.decision)}
                </span>
              </header>
              <p>{item.rationale.join(" ")}</p>
              {item.result ? (
                <>
                  <p className="assessment-result">
                    <strong>Recorded observation:</strong> {displayValue(item.result.measurement)}{" "}
                    {item.result.unit ?? ""} · {item.result.reliability} reliability · next reviewed
                    interval ends {new Date(item.result.next_reassessment_at).toLocaleDateString()}
                  </p>
                  <div className="assessment-capability">
                    {item.result.capability_estimate ? (
                      <p>
                        <strong>Derived protocol-specific estimate:</strong>{" "}
                        {displayValue(item.result.capability_estimate.estimate)}{" "}
                        {item.result.capability_estimate.unit_or_scale} ·{" "}
                        {item.result.capability_estimate.confidence} confidence ·{" "}
                        {statusLabel(item.result.capability_estimate_status)}
                      </p>
                    ) : (
                      <p>
                        <strong>Capability interpretation:</strong>{" "}
                        {item.result.capability_estimate_status === "ready"
                          ? "A current reviewed policy is available."
                          : "Unavailable until an evidence-linked policy is approved."}
                      </p>
                    )}
                    {item.result.capability_estimate_status === "ready" ? (
                      <button
                        type="button"
                        disabled={state === "saving"}
                        onClick={() => void createCapabilityEstimate(item.result!.performance_id)}
                      >
                        {state === "saving" ? "Interpreting…" : "Create reviewed estimate"}
                      </button>
                    ) : null}
                    {item.result.capability_estimate ? (
                      <details>
                        <summary>Estimate method and policy</summary>
                        <p>
                          Method {item.result.capability_estimate.calculation_method} · rule{" "}
                          {item.result.capability_estimate.rule_version} · source observations{" "}
                          {item.result.capability_estimate.source_observation_ids.length}
                        </p>
                        <p>
                          <strong>Applicability:</strong>{" "}
                          {item.result.capability_estimate.applicability_notes}
                        </p>
                        <p>
                          <strong>Uncertainty:</strong>{" "}
                          {item.result.capability_estimate.uncertainty}
                        </p>
                      </details>
                    ) : null}
                  </div>
                </>
              ) : item.result_status === "ready" ? (
                <AssessmentResultForm
                  apiBaseUrl={apiBaseUrl}
                  athleteId={athleteId}
                  runId={workflow.latest_run!.run_id}
                  decision={item}
                  onSaved={async () => {
                    await load();
                    await onChanged();
                  }}
                />
              ) : null}
              {item.result_status === "safety_review_required" ? (
                <aside className="review-boundary">
                  <strong>Fresh readiness review required.</strong>
                  <span>
                    This selection ended with a listed stop condition. It cannot accept a result;
                    submit a new current readiness report before starting another assessment run.
                  </span>
                </aside>
              ) : null}
              <AssessmentAttemptHistory attempts={item.attempts} />
              <details>
                <summary>Instructions and provenance</summary>
                <ol>
                  {item.protocol_instructions.map((instruction) => (
                    <li key={instruction}>{instruction}</li>
                  ))}
                </ol>
                <p><strong>Result entry:</strong> {item.result_entry_instructions}</p>
                <p><strong>Applicability:</strong> {item.applicability_notes}</p>
                <p><strong>Uncertainty:</strong> {item.uncertainty}</p>
                <p className="form-help">
                  Protocol {item.protocol_version} · review {item.review_version} ·{" "}
                  {item.evidence_claim_ids.length} linked evidence claim(s)
                </p>
                {item.result ? (
                  <p className="form-help">
                    Reassessment interval source review{" "}
                    {item.result.reassessment_interval_source_review_id}
                  </p>
                ) : null}
              </details>
            </article>
          ))}
        </div>
      ) : null}

      {workflow?.can_start_run ? (
        <details className="assessment-start">
          <summary>Start governed assessment selection</summary>
          <form className="assessment-form" onSubmit={startRun}>
            <label>
              Environment
              <select value={environmentId} onChange={(event) => setEnvironmentId(event.target.value)}>
                {workflow.environments.map((item) => (
                  <option value={item.environment_id} key={item.environment_id}>{item.name}</option>
                ))}
              </select>
            </label>
            <label>
              Body mass, kg <span>optional; used only when a reviewed protocol requires it</span>
              <input
                type="number"
                min="0.1"
                step="0.1"
                value={bodyMass}
                onChange={(event) => setBodyMass(event.target.value)}
              />
            </label>
            <details className="assessment-history">
              <summary>Add domain training history</summary>
              <div className="assessment-history__grid">
                {capabilityDomains.map(([domain, label]) => (
                  <label key={domain}>
                    {label}, months
                    <input
                      type="number"
                      min="0"
                      step="1"
                      value={trainingHistory[domain] ?? ""}
                      onChange={(event) =>
                        setTrainingHistory((current) => ({
                          ...current,
                          [domain]: event.target.value,
                        }))
                      }
                    />
                  </label>
                ))}
              </div>
            </details>
            <div className="paired-fields">
              <label>
                Practiced skill tags <span>optional, one per line</span>
                <textarea value={skills} onChange={(event) => setSkills(event.target.value)} rows={3} />
              </label>
              <label>
                Recent exposure tags <span>optional, one per line</span>
                <textarea value={exposures} onChange={(event) => setExposures(event.target.value)} rows={3} />
              </label>
            </div>
            <label>
              Report reliability
              <select value={reliability} onChange={(event) => setReliability(event.target.value as Confidence)}>
                <option value="moderate">Reasonably certain</option>
                <option value="high">Very certain</option>
                <option value="low">Some details are uncertain</option>
                <option value="unknown">Unknown</option>
              </select>
            </label>
            <p className="form-help">
              Equipment is derived from the selected persisted environment. This form cannot submit
              screening, injury, symptom, or health classifications.
            </p>
            <button type="submit" disabled={state === "saving"}>
              {state === "saving" ? "Selecting…" : "Select appropriate assessments"}
            </button>
          </form>
        </details>
      ) : null}
    </section>
  );
}
