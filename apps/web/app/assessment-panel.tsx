"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  buildAssessmentResultCommand,
  buildAssessmentRunCommand,
  fetchAssessmentWorkflow,
  submitAssessmentCapabilityEstimate,
  submitAssessmentResult,
  submitAssessmentRun,
  type AssessmentDecisionProjection,
  type AssessmentWorkflowProjection,
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
      const command = buildAssessmentResultCommand(decision, value, reliability);
      await submitAssessmentResult(
        apiBaseUrl,
        athleteId,
        runId,
        decision.selection_id,
        command,
      );
      await onSaved();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to record this result.");
      setState("error");
    }
  }

  return (
    <form className="assessment-result-form" onSubmit={submit}>
      <label>
        {schema.label}
        {schema.measurement_type === "category" ? (
          <select value={value} onChange={(event) => setValue(event.target.value)}>
            {schema.allowed_values.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        ) : (
          <input
            type="number"
            required
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
      <button type="submit" disabled={state === "saving"}>
        {state === "saving" ? "Recording…" : "Record result observation"}
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
}: {
  apiBaseUrl: string;
  athleteId: string;
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
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to start assessment selection.");
      setState("error");
    }
  }

  async function createCapabilityEstimate(performanceId: string) {
    setState("saving");
    setMessage("");
    try {
      await submitAssessmentCapabilityEstimate(apiBaseUrl, athleteId, performanceId);
      await load();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Unable to create the capability estimate.",
      );
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
                  ).toLocaleDateString()}`
                : "Operator review required"}
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
        </dl>
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
                  onSaved={load}
                />
              ) : null}
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
