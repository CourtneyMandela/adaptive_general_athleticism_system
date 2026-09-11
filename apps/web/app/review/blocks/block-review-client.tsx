"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import {
  fetchBlockPreparation,
  submitBlockPlan,
  type BlockPlanCreationResult,
  type BlockPreparationProjection,
  type OperatorBlockPlanRequest,
} from "@/lib/block-review";
import {
  fetchPreparedFirstBlock,
  ratifyPreparedFirstBlock,
  type PreparedFirstBlockProjection,
} from "@/lib/prepared-first-block";

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

function BlockReceipt({ result }: { result: BlockPlanCreationResult }) {
  return (
    <section className="resource-receipt" aria-labelledby="block-receipt-title">
      <p className="eyebrow">Immutable block receipt</p>
      <h2 id="block-receipt-title">{label(result.block_plan.status)} block recorded</h2>
      <p>{result.decision_record.decision}</p>
      <dl className="review-metadata">
        <div><dt>Block</dt><dd>{result.block_plan.id}</dd></div>
        <div><dt>Decision audit</dt><dd>{result.decision_record.id}</dd></div>
        <div><dt>Dates</dt><dd>{result.block_plan.starts_on} – {result.block_plan.ends_on}</dd></div>
        <div><dt>Budget</dt><dd>{result.block_plan.weekly_budget_minutes} min/week</dd></div>
      </dl>
      <div className="block-allocation-grid">
        {result.block_plan.allocations.map((allocation) => (
          <article key={allocation.id} className="block-allocation">
            <header>
              <strong>{label(allocation.priority_state)}</strong>
              <span className={`status-badge status-badge--${allocation.status}`}>
                {label(allocation.status)}
              </span>
            </header>
            <code>{allocation.adaptation_id}</code>
            <p>
              {allocation.allocated_weekly_minutes} allocated of {allocation.target_weekly_minutes}
              {" "}target minutes · {allocation.sessions_per_week} session(s)
            </p>
            {allocation.issues.length ? (
              <ul>
                {allocation.issues.map((issue) => (
                  <li key={`${issue.code}:${issue.detail}`}>
                    <strong>{label(issue.code)}:</strong> {issue.detail}
                  </li>
                ))}
              </ul>
            ) : null}
          </article>
        ))}
      </div>
      <details>
        <summary>Reviewer authority and provenance audit</summary>
        <ul>{result.decision_record.evidence.map((item) => <li key={item}>{item}</li>)}</ul>
      </details>
      <p className="form-help">
        This record contains no week, session, prescription, progression, or workout.
      </p>
      <Link href={`/review/weeks?blockId=${result.block_plan.id}`} className="primary-button">
        Prepare Week 1 inputs
      </Link>
    </section>
  );
}

function nextMondayIso(): string {
  const day = new Date();
  day.setHours(12, 0, 0, 0);
  day.setDate(day.getDate() + ((8 - day.getDay()) % 7));
  const year = day.getFullYear();
  const month = String(day.getMonth() + 1).padStart(2, "0");
  const date = String(day.getDate()).padStart(2, "0");
  return `${year}-${month}-${date}`;
}

function PreparedFirstBlockPanel({ strategyId }: { strategyId: string }) {
  const [startsOn, setStartsOn] = useState(nextMondayIso);
  const [projection, setProjection] = useState<PreparedFirstBlockProjection | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function load(date = startsOn) {
    setBusy(true);
    setMessage("");
    setConfirmed(false);
    try {
      setProjection(await fetchPreparedFirstBlock(apiBaseUrl, strategyId, date));
    } catch (error) {
      setProjection(null);
      setMessage(error instanceof Error ? error.message : "Unable to prepare the first block.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    let active = true;
    fetchPreparedFirstBlock(apiBaseUrl, strategyId, startsOn)
      .then((result) => {
        if (active) setProjection(result);
      })
      .catch((error: unknown) => {
        if (active) {
          setProjection(null);
          setMessage(error instanceof Error ? error.message : "Unable to prepare the first block.");
        }
      });
    return () => {
      active = false;
    };
  }, [startsOn, strategyId]);

  async function accept() {
    if (!projection?.candidate || !confirmed) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await ratifyPreparedFirstBlock(
        apiBaseUrl,
        strategyId,
        projection.candidate,
      );
      setProjection({
        ...projection,
        status: "accepted",
        message: result.created
          ? "The first block was recorded with immutable provenance."
          : "This exact first block was already recorded.",
        candidate: {
          ...projection.candidate,
          status: "accepted",
          accepted_result: result.result,
        },
      });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to accept the prepared block.");
    } finally {
      setBusy(false);
    }
  }

  if (projection?.candidate?.accepted_result) {
    return <BlockReceipt result={projection.candidate.accepted_result} />;
  }

  return (
    <section className="governed-context" aria-labelledby="prepared-first-block-title">
      <header>
        <div>
          <p className="eyebrow">Prepared first block</p>
          <h2 id="prepared-first-block-title">Let AGAS assemble the governed envelope</h2>
          <p>
            Choose when Week 1 begins. The server selects the exact ratified demands, policy,
            budget, and four-week boundary from this athlete&apos;s records.
          </p>
        </div>
        {projection ? (
          <span className={`status-badge status-badge--${projection.status}`}>
            {label(projection.status)}
          </span>
        ) : null}
      </header>
      <div className="review-input">
        <label htmlFor="prepared-block-start">Week 1 starts Monday</label>
        <input
          id="prepared-block-start"
          type="date"
          value={startsOn}
          onChange={(event) => setStartsOn(event.target.value)}
        />
        <button type="button" className="secondary-button" disabled={busy} onClick={() => void load()}>
          {busy ? "Checking exact state…" : "Prepare this start date"}
        </button>
      </div>
      {projection ? <p>{projection.message}</p> : null}
      {projection?.blockers.length ? (
        <ul className="form-error">
          {projection.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}
        </ul>
      ) : null}
      {projection?.candidate ? (
        <>
          <dl className="review-metadata">
            <div><dt>Dates</dt><dd>{projection.candidate.starts_on} – {projection.candidate.ends_on}</dd></div>
            <div><dt>Duration</dt><dd>{projection.candidate.duration_weeks} weeks</dd></div>
            <div><dt>Weekly envelope</dt><dd>{projection.candidate.weekly_budget_minutes} minutes</dd></div>
            <div><dt>Expected result</dt><dd>{label(projection.candidate.expected_status)}</dd></div>
          </dl>
          <div className="block-allocation-grid">
            {projection.candidate.expected_allocations.map((allocation) => (
              <article className="block-allocation" key={allocation.adaptation_id}>
                <strong>{label(allocation.priority_state)}</strong>
                <p>
                  {allocation.allocated_weekly_minutes} minutes/week across{" "}
                  {allocation.sessions_per_week} sessions
                </p>
              </article>
            ))}
          </div>
          <aside className="review-boundary">
            <strong>This is not yet a workout.</strong>
            <span>{projection.candidate.safety_boundary}</span>
          </aside>
          <details>
            <summary>Why AGAS prepared these exact values</summary>
            <p>{projection.candidate.construction_basis}</p>
            <p>{projection.candidate.applicability_rationale}</p>
            <p><strong>Remaining uncertainty:</strong> {projection.candidate.uncertainty}</p>
            <code>{projection.candidate.content_digest}</code>
          </details>
          <label className="review-confirmation">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(event) => setConfirmed(event.target.checked)}
            />
            <span>
              I reviewed this exact athlete-specific block and understand that Week 1 and its
              safety gate are still separate steps.
            </span>
          </label>
          <button
            type="button"
            className="primary-button"
            disabled={!confirmed || busy}
            onClick={() => void accept()}
          >
            {busy ? "Recording exact block…" : "Accept and record first block"}
          </button>
        </>
      ) : null}
      {message ? <p className="form-error" role="alert">{message}</p> : null}
    </section>
  );
}

function BlockContextForm({
  projection,
}: {
  projection: BlockPreparationProjection;
}) {
  const [demandByPriority, setDemandByPriority] = useState<Record<string, string>>({});
  const [policyId, setPolicyId] = useState("");
  const [weeklyBudget, setWeeklyBudget] = useState("");
  const [startsOn, setStartsOn] = useState("");
  const [durationWeeks, setDurationWeeks] = useState("");
  const [constraintsText, setConstraintsText] = useState("");
  const [applicabilityRationale, setApplicabilityRationale] = useState("");
  const [uncertainty, setUncertainty] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<BlockPlanCreationResult | null>(null);

  const selectedHistory = projection.priorities.flatMap((option) => {
    const selectedId = demandByPriority[option.priority.id];
    return option.demand_history.filter((item) => item.resource_demand.id === selectedId);
  });
  const everyPrioritySelected = projection.priorities.every(
    (option) => Boolean(demandByPriority[option.priority.id]),
  );
  const selectedMinimum = selectedHistory.reduce(
    (total, item) => total + item.resource_demand.minimum_weekly_minutes,
    0,
  );
  const selectedTarget = selectedHistory.reduce(
    (total, item) => total + item.resource_demand.target_weekly_minutes,
    0,
  );
  const selectedPolicy = projection.resource_allocation_policies.find(
    (policy) => policy.id === policyId,
  );
  const hasMissingInputs =
    projection.priorities.some((option) => option.demand_history.length === 0) ||
    projection.resource_allocation_policies.length === 0;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!confirmed) return;
    setBusy(true);
    setMessage("");
    try {
      if (!everyPrioritySelected) throw new Error("Select one demand for every strategy priority.");
      const constraints = constraintsText
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean);
      const request: OperatorBlockPlanRequest = {
        resource_demand_ids: projection.priorities.map(
          (option) => demandByPriority[option.priority.id],
        ),
        resource_allocation_policy_id: policyId,
        weekly_budget_minutes: positiveInteger(weeklyBudget, "Weekly budget"),
        starts_on: startsOn,
        duration_weeks: positiveInteger(durationWeeks, "Duration"),
        constraints,
        generated_at: new Date().toISOString(),
        applicability_rationale: applicabilityRationale,
        uncertainty,
      };
      setResult(await submitBlockPlan(apiBaseUrl, projection.strategy.id, request));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to create the reviewed block.");
    } finally {
      setBusy(false);
    }
  }

  if (result) return <BlockReceipt result={result} />;

  return (
    <form className="governed-context block-context-form" onSubmit={submit}>
      <header>
        <div>
          <p className="eyebrow">Exact historical selection</p>
          <h2>Choose one demand per priority</h2>
          <p>
            Nothing is current by implication. Every priority, including DEFER, requires one
            explicit historical record.
          </p>
        </div>
        <span className="status-badge">
          {selectedHistory.length}/{projection.priorities.length} selected
        </span>
      </header>

      <div className="block-priority-list">
        {projection.priorities.map((option) => (
          <fieldset key={option.priority.id} className="block-priority-demand">
            <legend>#{option.priority.rank} · {option.adaptation.name}</legend>
            <p>
              <span className="status-badge">{label(option.priority.state)}</span>{" "}
              {label(option.adaptation.domain)}
            </p>
            {option.demand_history.length ? (
              <div className="block-demand-options">
                {option.demand_history.map((history) => (
                  <label key={history.resource_demand.id}>
                    <input
                      type="radio"
                      name={`priority-${option.priority.id}`}
                      checked={demandByPriority[option.priority.id] === history.resource_demand.id}
                      onChange={() => setDemandByPriority((current) => ({
                        ...current,
                        [option.priority.id]: history.resource_demand.id,
                      }))}
                    />
                    <span>
                      <strong>{history.resource_demand.demand_version}</strong>
                      <small>
                        {history.resource_demand.minimum_weekly_minutes}–{history.resource_demand.target_weekly_minutes}
                        {" "}min · {history.resource_demand.sessions_per_week} session(s) ·{" "}
                        {history.exercise_resolution?.status ?? "deferred"}
                      </small>
                      <small>{history.resource_demand.rationale}</small>
                      {history.exercise_resolution?.unresolved_issues.length ? (
                        <small className="block-warning">
                          {history.exercise_resolution.unresolved_issues.length} unresolved
                          {" "}exercise-resolution issue(s)
                        </small>
                      ) : null}
                      <code>{history.resource_demand.id}</code>
                    </span>
                  </label>
                ))}
              </div>
            ) : (
              <p className="form-error">
                No demand history exists. Return to resource-demand review for this priority.
              </p>
            )}
          </fieldset>
        ))}
      </div>

      <section className="resource-section">
        <h3>Resource-allocation policy</h3>
        <p className="form-help">
          Policy presence is not scientific approval. Select the exact immutable policy reviewed
          for this block context.
        </p>
        <div className="block-policy-grid">
          {projection.resource_allocation_policies.map((policy) => (
            <label key={policy.id}>
              <input
                type="radio"
                name="allocation-policy"
                checked={policyId === policy.id}
                onChange={() => setPolicyId(policy.id)}
              />
              <span>
                <strong>{policy.policy_version}</strong>
                <small>
                  DEVELOP {policy.develop_weight} · MAINTAIN {policy.maintain_weight} · EXPOSE{" "}
                  {policy.expose_weight}
                </small>
                <small>Partial exercise resolution {policy.allow_partial_exercise_resolution ? "allowed" : "blocked"}</small>
                <code>{policy.id}</code>
              </span>
            </label>
          ))}
        </div>
        {projection.resource_allocation_policies.length === 0 ? (
          <p className="form-error">No persisted resource-allocation policy is available.</p>
        ) : null}
      </section>

      <section className="resource-section">
        <h3>Explicit block context</h3>
        <div className="block-context-grid">
          <label>
            Weekly training budget (minutes)
            <input type="number" min="1" value={weeklyBudget} onChange={(event) => setWeeklyBudget(event.target.value)} required />
          </label>
          <label>
            Start date
            <input type="date" value={startsOn} onChange={(event) => setStartsOn(event.target.value)} required />
          </label>
          <label>
            Duration
            <select value={durationWeeks} onChange={(event) => setDurationWeeks(event.target.value)} required>
              <option value="" disabled>Select 4–6 weeks</option>
              <option value="4">4 weeks</option>
              <option value="5">5 weeks</option>
              <option value="6">6 weeks</option>
            </select>
          </label>
        </div>
        <label>
          Reviewed constraints (one per line; leave empty only when none apply)
          <textarea value={constraintsText} onChange={(event) => setConstraintsText(event.target.value)} rows={4} />
        </label>
        <div className="context-review-fields">
          <label>
            Applicability rationale
            <textarea value={applicabilityRationale} onChange={(event) => setApplicabilityRationale(event.target.value)} rows={4} required />
          </label>
          <label>
            Known uncertainty
            <textarea value={uncertainty} onChange={(event) => setUncertainty(event.target.value)} rows={4} required />
          </label>
        </div>
      </section>

      <section className="block-context-summary" aria-label="Selected block context summary">
        <strong>Selection summary — not a recommendation</strong>
        <span>Selected minimum: {selectedMinimum} min/week</span>
        <span>Selected targets: {selectedTarget} min/week</span>
        <span>Entered budget: {weeklyBudget || "blank"} min/week</span>
        <span>Policy: {selectedPolicy?.policy_version ?? "unselected"}</span>
      </section>

      <label className="context-confirmation">
        <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
        <span>
          I reviewed every demand history, policy, budget, date, duration, constraint, rationale,
          and uncertainty field. I understand that partial or infeasible block status may be correct.
        </span>
      </label>
      <button
        type="submit"
        className="primary-button"
        disabled={!confirmed || busy || hasMissingInputs || !everyPrioritySelected || !policyId}
      >
        {busy ? "Allocating and recording…" : "Create reviewed block"}
      </button>
      <p className="form-help">
        The deterministic allocator may leave budget unused or produce a partial/infeasible block.
        This action does not schedule Week 1.
      </p>
      {message ? <p className="form-error" role="alert">{message}</p> : null}
    </form>
  );
}

export function BlockReviewClient({ initialStrategyId }: { initialStrategyId: string }) {
  const [strategyId, setStrategyId] = useState(initialStrategyId);
  const [projection, setProjection] = useState<BlockPreparationProjection | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function loadProjection() {
    const normalized = strategyId.trim();
    setMessage("");
    setProjection(null);
    if (!uuidPattern.test(normalized)) {
      setMessage("Enter a valid strategy UUID.");
      return;
    }
    setBusy(true);
    try {
      setProjection(await fetchBlockPreparation(apiBaseUrl, normalized));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load block preparation.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="review-shell">
      <header className="review-topbar">
        <div>
          <p className="eyebrow">AGAS · Strategy to block</p>
          <h1>Prepare the first training block</h1>
          <p>
            Pick a Monday. AGAS will assemble the exact athlete-specific resource envelope from
            the governed work already completed.
          </p>
        </div>
        <nav className="review-route-links" aria-label="Reviewer routes">
          <Link href="/review/queue" className="text-link">Queue</Link>
          <Link href="/review" className="text-link">Initial strategy</Link>
          <Link href="/review/resource-demands" className="text-link">Resource demands</Link>
          <Link href="/review/weeks" className="text-link">Week 1</Link>
          <Link href="/review/post-block" className="text-link">Post-block</Link>
          <Link href="/" className="text-link">Athlete PWA</Link>
        </nav>
      </header>
      <aside className="review-boundary">
        <strong>The start date is your choice; the technical values are governed.</strong>
        <span>
          The server derives demand, policy, budget, and duration from exact ratified state. If
          anything is missing or ambiguous, it explains the blocker instead of making up a plan.
        </span>
      </aside>
      <section className="review-input resource-strategy-loader">
        <label htmlFor="block-strategy-id">Long-range strategy ID</label>
        <input id="block-strategy-id" value={strategyId} onChange={(event) => setStrategyId(event.target.value)} placeholder="00000000-0000-4000-8000-000000000000" />
        <button type="button" className="primary-button" disabled={busy} onClick={() => void loadProjection()}>
          {busy ? "Loading exact history…" : "Load block preparation"}
        </button>
      </section>
      {message ? <p className="form-error review-message" role="alert">{message}</p> : null}
      {projection ? (
        <>
          <section className="review-preparation resource-strategy-summary">
            <header>
              <div>
                <p className="eyebrow">Persisted strategy hypothesis</p>
                <h2>Review the block boundary</h2>
                <p>{projection.strategy.block_hypothesis}</p>
                <code>{projection.strategy.id}</code>
              </div>
              <span className="status-badge">{projection.existing_blocks.length} historical block(s)</span>
            </header>
            {projection.existing_blocks.length ? (
              <details>
                <summary>Inspect existing immutable blocks</summary>
                <div className="resource-history">
                  {projection.existing_blocks.map((block) => (
                    <article key={block.id}>
                      <strong>{label(block.status)} · {block.duration_weeks} weeks</strong>
                      <code>{block.id}</code>
                      <span>{block.starts_on} – {block.ends_on} · {block.weekly_budget_minutes} min/week</span>
                    </article>
                  ))}
                </div>
              </details>
            ) : null}
          </section>
          <PreparedFirstBlockPanel strategyId={projection.strategy.id} />
          <details className="governed-context">
            <summary>Advanced recovery: manually assemble a block</summary>
            <p className="form-help">
              Use this only when the prepared path is blocked and an authorized reviewer needs to
              inspect or recover exceptional historical state.
            </p>
            <BlockContextForm projection={projection} />
          </details>
        </>
      ) : null}
    </main>
  );
}
