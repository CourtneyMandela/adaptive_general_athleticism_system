"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import {
  fetchFirstWeekPreparation,
  submitFirstWeekPlan,
  type CostLevel,
  type FirstWeekPreparationProjection,
  type IntensityTarget,
  type OperatorWeeklyPlanRequest,
  type SessionSection,
  type WeeklyPlanCreationResult,
} from "@/lib/first-week-review";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function label(value: string): string {
  return value.replaceAll("_", " ");
}

function positiveInteger(value: string, name: string): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) throw new Error(`${name} must be positive.`);
  return parsed;
}

function nonNegativeInteger(value: string, name: string): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 0) throw new Error(`${name} cannot be negative.`);
  return parsed;
}

function localTimestamp(value: string, name: string): string {
  if (!value) throw new Error(`${name} is required.`);
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) throw new Error(`${name} is invalid.`);
  return parsed.toISOString();
}

type IntensityForm = { key: string; kind: string; first: string; second: string; text: string };
type PrescriptionForm = {
  reason: string; sets: string; doseMode: string; doseValue: string; intensity: IntensityForm[];
  rest: string; progression: string; substitution: string; duration: string; fatigue: string;
  observations: string[]; evidence: string[]; version: string;
};
type TemplateForm = {
  key: string; name: string; frequency: string; duration: string; fatigue: string;
  observations: string[]; evidence: string[]; version: string;
  items: Record<string, { included: boolean; order: string; section: string }>;
};
type WindowForm = { key: string; environment: string; startsAt: string; endsAt: string };

function toggle(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function buildIntensity(form: IntensityForm): IntensityTarget {
  if (form.kind === "bodyweight") return { kind: "bodyweight" };
  if (form.kind === "absolute_load") {
    return { kind: "absolute_load", value: Number(form.first), unit: form.text };
  }
  if (form.kind === "relative_load") {
    return { kind: "relative_load", percentage: Number(form.first), reference: form.text };
  }
  if (form.kind === "effort_rpe" || form.kind === "repetitions_in_reserve") {
    return { kind: form.kind, minimum: Number(form.first), maximum: Number(form.second) };
  }
  if (form.kind === "heart_rate_zone") {
    return { kind: "heart_rate_zone", zone: Number(form.first) };
  }
  if (form.kind === "pace") {
    return { kind: "pace", value: Number(form.first), unit: form.text };
  }
  if (form.kind === "technique") {
    return {
      kind: "technique",
      constraints: form.text.split("\n").map((item) => item.trim()).filter(Boolean),
    };
  }
  throw new Error("Every intensity target requires a type.");
}

function ProvenanceChoices({
  projection, observations, evidence, onObservations, onEvidence, showEvidence = true,
}: {
  projection: FirstWeekPreparationProjection; observations: string[]; evidence: string[];
  onObservations: (values: string[]) => void; onEvidence: (values: string[]) => void;
  showEvidence?: boolean;
}) {
  return (
    <details className="first-week-provenance">
      <summary>Observation and evidence lineage</summary>
      <div className="first-week-provenance-grid">
        {showEvidence ? <fieldset>
          <legend>Source observations</legend>
          {projection.source_observations.map((item) => (
            <label key={item.id}>
              <input type="checkbox" checked={observations.includes(item.id)} onChange={() => onObservations(toggle(observations, item.id))} />
              <span><strong>{label(item.observation_type)}</strong><small>{item.reliability} · {item.id}</small></span>
            </label>
          ))}
        </fieldset> : null}
        <fieldset>
          <legend>Evidence claims</legend>
          {projection.evidence_claims.map((item) => (
            <label key={item.id}>
              <input type="checkbox" checked={evidence.includes(item.id)} onChange={() => onEvidence(toggle(evidence, item.id))} />
              <span><strong>{item.claim}</strong><small>{item.evidence_strength} · {item.athlete_applicability} applicability</small></span>
            </label>
          ))}
        </fieldset>
      </div>
    </details>
  );
}

function IntensityFields({ form, onChange, onRemove }: { form: IntensityForm; onChange: (form: IntensityForm) => void; onRemove: () => void }) {
  return (
    <div className="intensity-row">
      <label>Type
        <select value={form.kind} onChange={(event) => onChange({ ...form, kind: event.target.value, first: "", second: "", text: "" })} required>
          <option value="" disabled>Select intensity type</option>
          <option value="absolute_load">Absolute load</option><option value="relative_load">Relative load</option>
          <option value="bodyweight">Bodyweight</option><option value="effort_rpe">Effort RPE</option>
          <option value="repetitions_in_reserve">Repetitions in reserve</option><option value="heart_rate_zone">Heart-rate zone</option>
          <option value="pace">Pace</option><option value="technique">Technique constraints</option>
        </select>
      </label>
      {form.kind === "absolute_load" || form.kind === "pace" ? <><label>Value<input type="number" step="any" value={form.first} onChange={(event) => onChange({ ...form, first: event.target.value })} required /></label><label>Unit<input value={form.text} onChange={(event) => onChange({ ...form, text: event.target.value })} required /></label></> : null}
      {form.kind === "relative_load" ? <><label>Percentage<input type="number" step="any" value={form.first} onChange={(event) => onChange({ ...form, first: event.target.value })} required /></label><label>Reference<input value={form.text} onChange={(event) => onChange({ ...form, text: event.target.value })} required /></label></> : null}
      {form.kind === "effort_rpe" || form.kind === "repetitions_in_reserve" ? <><label>Minimum<input type="number" step="any" min="0" max="10" value={form.first} onChange={(event) => onChange({ ...form, first: event.target.value })} required /></label><label>Maximum<input type="number" step="any" min="0" max="10" value={form.second} onChange={(event) => onChange({ ...form, second: event.target.value })} required /></label></> : null}
      {form.kind === "heart_rate_zone" ? <label>Zone<input type="number" min="1" max="5" value={form.first} onChange={(event) => onChange({ ...form, first: event.target.value })} required /></label> : null}
      {form.kind === "technique" ? <label>Constraints (one per line)<textarea rows={2} value={form.text} onChange={(event) => onChange({ ...form, text: event.target.value })} required /></label> : null}
      <button type="button" className="text-button" onClick={onRemove}>Remove target</button>
    </div>
  );
}

function WeekReceipt({ result }: { result: WeeklyPlanCreationResult }) {
  return (
    <section className="resource-receipt">
      <p className="eyebrow">Immutable Week 1 receipt</p>
      <h2>{label(result.weekly_plan.status)} week recorded</h2>
      <p>{result.decision_record.decision}</p>
      <dl className="review-metadata">
        <div><dt>Weekly plan</dt><dd>{result.weekly_plan.id}</dd></div>
        <div><dt>Sessions</dt><dd>{result.weekly_plan.sessions.length}</dd></div>
        <div><dt>Issues</dt><dd>{result.weekly_plan.issues.length}</dd></div>
        <div><dt>Decision audit</dt><dd>{result.decision_record.id}</dd></div>
      </dl>
      {result.weekly_plan.issues.length ? <ul>{result.weekly_plan.issues.map((issue) => <li key={`${issue.code}:${issue.detail}`}><strong>{label(issue.code)}:</strong> {issue.detail}</li>)}</ul> : null}
      <details><summary>Authority and planning lineage</summary><ul>{result.decision_record.evidence.map((item) => <li key={item}>{item}</li>)}</ul></details>
    </section>
  );
}

function Preparation({ projection }: { projection: FirstWeekPreparationProjection }) {
  const active = projection.allocation_inputs.filter(
    (item) => item.allocation.allocated_weekly_minutes > 0,
  );
  const approvedPolicies = projection.scheduling_policy_options.filter(
    (item) => item.current_review?.decision === "approved",
  );
  return (
    <>
      <section className="review-preparation resource-strategy-summary">
        <header>
          <div>
            <p className="eyebrow">Persisted block hypothesis</p>
            <h2>Prepare Week 1 inputs</h2>
            <p>{projection.block.hypothesis}</p>
            <code>{projection.block.id}</code>
          </div>
          <span className={`status-badge status-badge--${projection.block.status}`}>
            {label(projection.block.status)} block
          </span>
        </header>
        <dl className="review-metadata">
          <div><dt>Week starts</dt><dd>{projection.block.starts_on}</dd></div>
          <div><dt>Budget</dt><dd>{projection.block.weekly_budget_minutes} min</dd></div>
          <div><dt>Active allocations</dt><dd>{active.length}</dd></div>
          <div><dt>Existing Week 1 plans</dt><dd>{projection.existing_first_week_plans.length}</dd></div>
        </dl>
      </section>

      <section className="governed-context first-week-preparation">
        <header>
          <div>
            <p className="eyebrow">Prescription lineage</p>
            <h2>Every active allocation needs an explicit dose</h2>
          </div>
          <span className="status-badge">{active.length} required</span>
        </header>
        <div className="block-allocation-grid">
          {active.map((item) => (
            <article key={item.allocation.id} className="block-allocation">
              <header>
                <strong>{item.adaptation.name}</strong>
                <span className="status-badge">{label(item.allocation.priority_state)}</span>
              </header>
              <p>{item.selected_exercise?.name ?? "No selected exercise"}</p>
              <p>
                {item.allocation.allocated_weekly_minutes} min · {item.allocation.sessions_per_week}
                {" "}session(s) · {label(item.exercise_resolution?.status ?? "unresolved")}
              </p>
              <details>
                <summary>Inspect stimulus and resolution rationale</summary>
                <p>{item.stimulus_requirement?.rationale}</p>
                <p>{item.exercise_resolution?.rationale}</p>
                <code>{item.allocation.id}</code>
              </details>
            </article>
          ))}
        </div>
      </section>

      <section className="governed-context first-week-preparation">
        <header><div><p className="eyebrow">Calendar authority</p><h2>Available reviewed inputs</h2></div></header>
        <div className="block-context-summary">
          <span>{projection.environments.length} environment(s)</span>
          <span>{approvedPolicies.length} currently approved scheduling policy option(s)</span>
          <span>{projection.source_observations.length} source observation(s)</span>
          <span>{projection.evidence_claims.length} evidence claim(s)</span>
        </div>
        {approvedPolicies.map((item) => (
          <article key={item.policy.id} className="block-allocation">
            <strong>{item.policy.policy_version}</strong>
            <p>
              {item.policy.minimum_high_fatigue_recovery_hours}h high-fatigue recovery · max{" "}
              {item.policy.maximum_sessions_per_day} session(s)/day
            </p>
            <p>{item.current_review?.applicability_rationale}</p>
            <code>{item.current_review?.id}</code>
          </article>
        ))}
        <p className="form-help">
          This page deliberately does not prefill sets, repetitions, intensity, rest, progression,
          session grouping, availability windows, or policy selection. The authenticated API now
          accepts the fully reviewed structured command assembled in the field-by-field workflow
          below.
        </p>
      </section>
    </>
  );
}

function FirstWeekAuthoringForm({ projection }: { projection: FirstWeekPreparationProjection }) {
  const active = projection.allocation_inputs.filter((item) => item.allocation.allocated_weekly_minutes > 0);
  const [prescriptions, setPrescriptions] = useState<Record<string, PrescriptionForm>>(() => Object.fromEntries(active.map((item) => [item.allocation.id, { reason: "", sets: "", doseMode: "", doseValue: "", intensity: [], rest: "", progression: "", substitution: "", duration: "", fatigue: "", observations: [], evidence: [], version: "" }])));
  const [templates, setTemplates] = useState<TemplateForm[]>([]);
  const [windows, setWindows] = useState<WindowForm[]>([]);
  const [availabilityObservations, setAvailabilityObservations] = useState<string[]>([]);
  const [availabilityVersion, setAvailabilityVersion] = useState("");
  const [policyId, setPolicyId] = useState("");
  const [applicability, setApplicability] = useState("");
  const [uncertainty, setUncertainty] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<WeeklyPlanCreationResult | null>(null);

  function updatePrescription(id: string, update: Partial<PrescriptionForm>) {
    setPrescriptions((current) => ({ ...current, [id]: { ...current[id], ...update } }));
  }

  function updateTemplate(key: string, update: Partial<TemplateForm>) {
    setTemplates((current) => current.map((item) => item.key === key ? { ...item, ...update } : item));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!confirmed) return;
    setBusy(true); setMessage("");
    try {
      const policy = projection.scheduling_policy_options.find((item) => item.policy.id === policyId);
      if (!policy?.current_review || policy.current_review.decision !== "approved") throw new Error("Select a currently approved scheduling policy review.");
      const request: OperatorWeeklyPlanRequest = {
        prescriptions: active.map((input) => {
          const form = prescriptions[input.allocation.id];
          const dose = positiveInteger(form.doseValue, `${input.adaptation.name} dose`);
          return {
            resource_allocation_id: input.allocation.id,
            reason_for_inclusion: form.reason,
            sets: positiveInteger(form.sets, `${input.adaptation.name} sets`),
            ...(form.doseMode === "repetitions" ? { repetitions_per_set: dose } : form.doseMode === "duration" ? { duration_seconds: dose } : (() => { throw new Error(`${input.adaptation.name} requires repetitions or duration.`); })()),
            intensity_targets: form.intensity.map(buildIntensity),
            rest_seconds: nonNegativeInteger(form.rest, `${input.adaptation.name} rest`),
            progression_rule_reference: form.progression,
            substitution_class: form.substitution,
            planned_duration_minutes: positiveInteger(form.duration, `${input.adaptation.name} planned duration`),
            fatigue_cost: form.fatigue as CostLevel,
            source_observation_ids: form.observations,
            evidence_claim_ids: form.evidence,
            rule_version: form.version,
          };
        }),
        session_templates: templates.map((template) => ({
          name: template.name,
          items: Object.entries(template.items).filter(([, item]) => item.included).map(([allocationId, item]) => ({ resource_allocation_id: allocationId, order_index: positiveInteger(item.order, `${template.name || "Session"} order`), section: item.section as SessionSection })).sort((a, b) => a.order_index - b.order_index),
          sessions_per_week: positiveInteger(template.frequency, `${template.name || "Session"} frequency`),
          planned_duration_minutes: positiveInteger(template.duration, `${template.name || "Session"} duration`),
          fatigue_cost: template.fatigue as CostLevel,
          source_observation_ids: template.observations,
          evidence_claim_ids: template.evidence,
          rule_version: template.version,
        })),
        availability: {
          week_start: projection.block.starts_on,
          windows: windows.map((window) => ({ environment_id: window.environment, starts_at: localTimestamp(window.startsAt, "Availability start"), ends_at: localTimestamp(window.endsAt, "Availability end") })),
          source_observation_ids: availabilityObservations,
          rule_version: availabilityVersion,
        },
        scheduling_policy_id: policy.policy.id,
        scheduling_policy_review_id: policy.current_review.id,
        prepared_at: new Date().toISOString(),
        applicability_rationale: applicability,
        uncertainty,
      };
      setResult(await submitFirstWeekPlan(apiBaseUrl, projection.block.id, request));
    } catch (error) { setMessage(error instanceof Error ? error.message : "Unable to create Week 1."); }
    finally { setBusy(false); }
  }

  if (result) return <WeekReceipt result={result} />;
  return (
    <form className="governed-context first-week-authoring" onSubmit={submit}>
      <header><div><p className="eyebrow">Explicit reviewed command</p><h2>Author complete Week 1 inputs</h2><p>Every dose and grouping starts blank. The scheduler—not this form—decides whether the result is feasible.</p></div></header>

      <section className="first-week-step">
        <h3>1. Prescriptions</h3>
        {active.map((input) => {
          const form = prescriptions[input.allocation.id];
          return <fieldset key={input.allocation.id} className="prescription-editor">
            <legend>{input.adaptation.name} · {input.selected_exercise?.name}</legend>
            <p className="form-help">{input.allocation.allocated_weekly_minutes} min/week across {input.allocation.sessions_per_week} allocation session(s). This is context, not a dose.</p>
            <label>Reason for inclusion<textarea rows={3} value={form.reason} onChange={(event) => updatePrescription(input.allocation.id, { reason: event.target.value })} required /></label>
            <div className="first-week-field-grid">
              <label>Sets<input type="number" min="1" value={form.sets} onChange={(event) => updatePrescription(input.allocation.id, { sets: event.target.value })} required /></label>
              <label>Dose dimension<select value={form.doseMode} onChange={(event) => updatePrescription(input.allocation.id, { doseMode: event.target.value, doseValue: "" })} required><option value="" disabled>Select reps or duration</option><option value="repetitions">Repetitions per set</option><option value="duration">Duration in seconds</option></select></label>
              <label>{form.doseMode === "duration" ? "Seconds" : "Repetitions"}<input type="number" min="1" value={form.doseValue} onChange={(event) => updatePrescription(input.allocation.id, { doseValue: event.target.value })} required /></label>
              <label>Rest (seconds)<input type="number" min="0" value={form.rest} onChange={(event) => updatePrescription(input.allocation.id, { rest: event.target.value })} required /></label>
              <label>Planned duration (minutes)<input type="number" min="1" value={form.duration} onChange={(event) => updatePrescription(input.allocation.id, { duration: event.target.value })} required /></label>
              <label>Fatigue cost<select value={form.fatigue} onChange={(event) => updatePrescription(input.allocation.id, { fatigue: event.target.value })} required><option value="" disabled>Select cost</option><option value="low">Low</option><option value="moderate">Moderate</option><option value="high">High</option></select></label>
              <label>Progression rule reference<input value={form.progression} onChange={(event) => updatePrescription(input.allocation.id, { progression: event.target.value })} required /></label>
              <label>Substitution class<input value={form.substitution} onChange={(event) => updatePrescription(input.allocation.id, { substitution: event.target.value })} required /></label>
              <label>Prescription rule version<input value={form.version} onChange={(event) => updatePrescription(input.allocation.id, { version: event.target.value })} required /></label>
            </div>
            <div className="intensity-list"><strong>Intensity targets</strong>{form.intensity.map((item) => <IntensityFields key={item.key} form={item} onChange={(next) => updatePrescription(input.allocation.id, { intensity: form.intensity.map((current) => current.key === item.key ? next : current) })} onRemove={() => updatePrescription(input.allocation.id, { intensity: form.intensity.filter((current) => current.key !== item.key) })} />)}<button type="button" className="secondary-button" onClick={() => updatePrescription(input.allocation.id, { intensity: [...form.intensity, { key: crypto.randomUUID(), kind: "", first: "", second: "", text: "" }] })}>Add intensity target</button></div>
            <ProvenanceChoices projection={projection} observations={form.observations} evidence={form.evidence} onObservations={(values) => updatePrescription(input.allocation.id, { observations: values })} onEvidence={(values) => updatePrescription(input.allocation.id, { evidence: values })} />
          </fieldset>;
        })}
      </section>

      <section className="first-week-step"><h3>2. Session composition</h3><p className="form-help">Create explicit containers. Inclusion, order, section, frequency, and duration are independent of allocation frequency.</p>
        {templates.map((template) => <fieldset key={template.key} className="template-editor"><legend>{template.name || "Unnamed session"}</legend>
          <div className="first-week-field-grid"><label>Name<input value={template.name} onChange={(event) => updateTemplate(template.key, { name: event.target.value })} required /></label><label>Sessions per week<input type="number" min="1" value={template.frequency} onChange={(event) => updateTemplate(template.key, { frequency: event.target.value })} required /></label><label>Duration (minutes)<input type="number" min="1" value={template.duration} onChange={(event) => updateTemplate(template.key, { duration: event.target.value })} required /></label><label>Fatigue cost<select value={template.fatigue} onChange={(event) => updateTemplate(template.key, { fatigue: event.target.value })} required><option value="" disabled>Select cost</option><option value="low">Low</option><option value="moderate">Moderate</option><option value="high">High</option></select></label><label>Template rule version<input value={template.version} onChange={(event) => updateTemplate(template.key, { version: event.target.value })} required /></label></div>
          <div className="template-items">{active.map((input) => { const item = template.items[input.allocation.id]; return <div key={input.allocation.id}><label className="inline-check"><input type="checkbox" checked={item.included} onChange={(event) => updateTemplate(template.key, { items: { ...template.items, [input.allocation.id]: { ...item, included: event.target.checked } } })} /><span>{input.selected_exercise?.name}</span></label><label>Order<input type="number" min="1" value={item.order} disabled={!item.included} onChange={(event) => updateTemplate(template.key, { items: { ...template.items, [input.allocation.id]: { ...item, order: event.target.value } } })} /></label><label>Section<select value={item.section} disabled={!item.included} onChange={(event) => updateTemplate(template.key, { items: { ...template.items, [input.allocation.id]: { ...item, section: event.target.value } } })}><option value="" disabled>Select section</option>{["preparation", "primary", "accessory", "conditioning", "cooldown", "other"].map((value) => <option key={value} value={value}>{label(value)}</option>)}</select></label></div>; })}</div>
          <ProvenanceChoices projection={projection} observations={template.observations} evidence={template.evidence} onObservations={(values) => updateTemplate(template.key, { observations: values })} onEvidence={(values) => updateTemplate(template.key, { evidence: values })} />
          <button type="button" className="text-button" onClick={() => setTemplates((current) => current.filter((item) => item.key !== template.key))}>Remove session template</button>
        </fieldset>)}
        <button type="button" className="secondary-button" onClick={() => setTemplates((current) => [...current, { key: crypto.randomUUID(), name: "", frequency: "", duration: "", fatigue: "", observations: [], evidence: [], version: "", items: Object.fromEntries(active.map((item) => [item.allocation.id, { included: false, order: "", section: "" }])) }])}>Add session template</button>
      </section>

      <section className="first-week-step"><h3>3. Dated availability</h3><p className="form-help">Week starts {projection.block.starts_on}. An explicit empty window list will produce scheduling infeasibility.</p>
        <div className="availability-windows">{windows.map((window) => <div key={window.key} className="availability-window"><div className="first-week-field-grid"><label>Environment<select value={window.environment} onChange={(event) => setWindows((current) => current.map((item) => item.key === window.key ? { ...item, environment: event.target.value } : item))} required><option value="" disabled>Select environment</option>{projection.environments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Starts<input type="datetime-local" value={window.startsAt} onChange={(event) => setWindows((current) => current.map((item) => item.key === window.key ? { ...item, startsAt: event.target.value } : item))} required /></label><label>Ends<input type="datetime-local" value={window.endsAt} onChange={(event) => setWindows((current) => current.map((item) => item.key === window.key ? { ...item, endsAt: event.target.value } : item))} required /></label></div><button type="button" className="text-button" onClick={() => setWindows((current) => current.filter((item) => item.key !== window.key))}>Remove window</button></div>)}</div>
        <button type="button" className="secondary-button" onClick={() => setWindows((current) => [...current, { key: crypto.randomUUID(), environment: "", startsAt: "", endsAt: "" }])}>Add availability window</button>
        <label>Availability rule version<input value={availabilityVersion} onChange={(event) => setAvailabilityVersion(event.target.value)} required /></label>
        <ProvenanceChoices projection={projection} observations={availabilityObservations} evidence={[]} onObservations={setAvailabilityObservations} onEvidence={() => undefined} showEvidence={false} />
      </section>

      <section className="first-week-step"><h3>4. Scheduling policy</h3><div className="block-policy-grid">{projection.scheduling_policy_options.map((option) => { const approved = option.current_review?.decision === "approved"; return <label key={option.policy.id} className={!approved ? "disabled-option" : ""}><input type="radio" name="weekly-policy" disabled={!approved} checked={policyId === option.policy.id} onChange={() => setPolicyId(option.policy.id)} /><span><strong>{option.policy.policy_version}</strong><small>{option.current_review ? `${label(option.current_review.decision)} · ${option.current_review.review_version}` : "No review"}</small><small>{option.current_review?.applicability_rationale}</small></span></label>; })}</div></section>
      <section className="first-week-step"><h3>5. Final review</h3><div className="context-review-fields"><label>Applicability rationale<textarea rows={4} value={applicability} onChange={(event) => setApplicability(event.target.value)} required /></label><label>Known uncertainty<textarea rows={4} value={uncertainty} onChange={(event) => setUncertainty(event.target.value)} required /></label></div><label className="context-confirmation"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /><span>I reviewed every dose, intensity target, rest interval, progression reference, session grouping, availability window, policy, provenance link, and uncertainty. I understand the scheduler may record an infeasible week.</span></label><button type="submit" className="primary-button" disabled={!confirmed || busy}>{busy ? "Validating and scheduling…" : "Create reviewed Week 1"}</button>{message ? <p className="form-error" role="alert">{message}</p> : null}</section>
    </form>
  );
}

export function FirstWeekReviewClient({ initialBlockId }: { initialBlockId: string }) {
  const [blockId, setBlockId] = useState(initialBlockId);
  const [projection, setProjection] = useState<FirstWeekPreparationProjection | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function load() {
    const normalized = blockId.trim();
    setMessage("");
    setProjection(null);
    if (!uuidPattern.test(normalized)) {
      setMessage("Enter a valid block UUID.");
      return;
    }
    setBusy(true);
    try {
      setProjection(await fetchFirstWeekPreparation(apiBaseUrl, normalized));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load Week 1 preparation.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="review-shell">
      <header className="review-topbar">
        <div>
          <p className="eyebrow">AGAS · Block to Week 1</p>
          <h1>First-week preparation</h1>
          <p>Inspect the exact exercise, evidence, environment, and policy lineage before dose.</p>
        </div>
        <nav className="review-route-links" aria-label="Reviewer routes">
          <Link href="/review/queue" className="text-link">Queue</Link>
          <Link href="/review/blocks" className="text-link">Blocks</Link>
          <Link href="/review/resource-demands" className="text-link">Resource demands</Link>
          <Link href="/review/post-block" className="text-link">Post-block</Link>
          <Link href="/" className="text-link">Athlete PWA</Link>
        </nav>
      </header>
      <aside className="review-boundary">
        <strong>No workout is generated from allocation minutes.</strong>
        <span>Dose, composition, dated availability, and policy remain explicit reviewed inputs.</span>
      </aside>
      <section className="review-input resource-strategy-loader">
        <label htmlFor="first-week-block-id">Block ID</label>
        <input id="first-week-block-id" value={blockId} onChange={(event) => setBlockId(event.target.value)} placeholder="00000000-0000-4000-8000-000000000000" />
        <button type="button" className="primary-button" disabled={busy} onClick={() => void load()}>
          {busy ? "Loading exact lineage…" : "Load Week 1 preparation"}
        </button>
      </section>
      {message ? <p className="form-error review-message" role="alert">{message}</p> : null}
      {projection ? <><Preparation projection={projection} /><FirstWeekAuthoringForm projection={projection} /></> : null}
    </main>
  );
}
