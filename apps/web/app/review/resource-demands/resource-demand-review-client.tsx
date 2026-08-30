"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import {
  costLevels,
  fetchResourceDemandPreparation,
  impactLevels,
  lateralities,
  loadabilities,
  loadingTypes,
  movementPatterns,
  submitResourceDemand,
  velocityCharacteristics,
  type CostLevel,
  type ImpactLevel,
  type Laterality,
  type Loadability,
  type LoadingType,
  type MovementPattern,
  type OperatorResourceDemandRequest,
  type ResourceDemandEvidenceClaim,
  type ResourceDemandObservation,
  type ResourceDemandPreparationProjection,
  type ResourceDemandPreparationResult,
  type VelocityCharacteristic,
} from "@/lib/resource-demand-review";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function label(value: string): string {
  return value.replaceAll("_", " ");
}

function toggle<T extends string>(values: T[], value: T, checked: boolean): T[] {
  return checked ? [...values, value] : values.filter((item) => item !== value);
}

function positiveInteger(value: string, name: string): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`${name} must be a positive integer.`);
  }
  return parsed;
}

function MultiCheck<T extends string>({
  legend,
  values,
  selected,
  onChange,
}: {
  legend: string;
  values: readonly T[];
  selected: T[];
  onChange: (values: T[]) => void;
}) {
  return (
    <fieldset className="resource-check-group">
      <legend>{legend}</legend>
      <div className="resource-check-grid">
        {values.map((value) => (
          <label key={value}>
            <input
              type="checkbox"
              checked={selected.includes(value)}
              onChange={(event) => onChange(toggle(selected, value, event.target.checked))}
            />
            <span>{label(value)}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function ProvenanceSelector({
  observations,
  evidenceClaims,
  selectedObservationIds,
  selectedEvidenceIds,
  onObservationsChange,
  onEvidenceChange,
}: {
  observations: ResourceDemandObservation[];
  evidenceClaims: ResourceDemandEvidenceClaim[];
  selectedObservationIds: string[];
  selectedEvidenceIds: string[];
  onObservationsChange: (values: string[]) => void;
  onEvidenceChange: (values: string[]) => void;
}) {
  return (
    <section className="resource-provenance" aria-labelledby="resource-provenance-title">
      <header>
        <div>
          <p className="eyebrow">Explicit lineage</p>
          <h3 id="resource-provenance-title">Observation and evidence provenance</h3>
        </div>
        <span className="status-badge">
          {selectedObservationIds.length} observation · {selectedEvidenceIds.length} claim
        </span>
      </header>
      <div className="resource-option-grid">
        <fieldset className="resource-option-list">
          <legend>Strategy observations</legend>
          {observations.map((observation) => (
            <label key={observation.id}>
              <input
                type="checkbox"
                checked={selectedObservationIds.includes(observation.id)}
                onChange={(event) =>
                  onObservationsChange(
                    toggle(selectedObservationIds, observation.id, event.target.checked),
                  )
                }
              />
              <span>
                <strong>{label(observation.observation_type)}</strong>
                <small>
                  {String(observation.measurement)} {observation.unit ?? ""} · {observation.reliability}
                </small>
                <code>{observation.id}</code>
              </span>
            </label>
          ))}
        </fieldset>
        <fieldset className="resource-option-list">
          <legend>Strategy evidence claims</legend>
          {evidenceClaims.map((claim) => (
            <label key={claim.id}>
              <input
                type="checkbox"
                checked={selectedEvidenceIds.includes(claim.id)}
                onChange={(event) =>
                  onEvidenceChange(toggle(selectedEvidenceIds, claim.id, event.target.checked))
                }
              />
              <span>
                <strong>{claim.claim}</strong>
                <small>
                  {claim.evidence_strength} strength · {claim.athlete_applicability} applicability
                </small>
                <code>{claim.id}</code>
              </span>
            </label>
          ))}
        </fieldset>
      </div>
      <p className="form-help">
        Nothing is preselected. Inclusion asserts that this exact record supports the reviewed
        stimulus and demand.
      </p>
    </section>
  );
}

function ResourceDemandReceipt({
  result,
  strategyId,
}: {
  result: ResourceDemandPreparationResult;
  strategyId: string;
}) {
  return (
    <section className="resource-receipt" aria-labelledby="resource-receipt-title">
      <p className="eyebrow">Immutable preparation receipt</p>
      <h2 id="resource-receipt-title">
        {result.exercise_resolution
          ? `${label(result.exercise_resolution.status)} resolution recorded`
          : "Deferred demand recorded"}
      </h2>
      <p>{result.decision_record.decision}</p>
      <dl className="review-metadata">
        <div><dt>Resource demand</dt><dd>{result.resource_demand.id}</dd></div>
        <div><dt>Stimulus requirement</dt><dd>{result.stimulus_requirement?.id ?? "None — deferred"}</dd></div>
        <div><dt>Exercise resolution</dt><dd>{result.exercise_resolution?.id ?? "None — deferred"}</dd></div>
        <div><dt>Decision audit</dt><dd>{result.decision_record.id}</dd></div>
      </dl>
      {result.exercise_resolution?.unresolved_issues.length ? (
        <div className="resource-issues">
          <strong>Resolution limitations remain explicit</strong>
          <ul>
            {result.exercise_resolution.unresolved_issues.map((issue) => (
              <li key={`${issue.code}:${issue.detail}`}>
                <strong>{label(issue.code)}:</strong> {issue.detail}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <details>
        <summary>Reviewer authority and provenance audit</summary>
        <ul>
          {result.decision_record.evidence.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </details>
      <Link
        href={`/review/blocks?strategyId=${encodeURIComponent(strategyId)}`}
        className="primary-button"
      >
        Review block context
      </Link>
    </section>
  );
}

function ResourceDemandEditor({
  projection,
  priorityOption,
  onCreated,
}: {
  projection: ResourceDemandPreparationProjection;
  priorityOption: ResourceDemandPreparationProjection["priorities"][number];
  onCreated: () => Promise<void>;
}) {
  const deferred = priorityOption.priority.state === "defer";
  const [environmentId, setEnvironmentId] = useState("");
  const [resolverPolicyId, setResolverPolicyId] = useState("");
  const [exerciseCandidateIds, setExerciseCandidateIds] = useState<string[]>([]);
  const [selectedMovementPatterns, setSelectedMovementPatterns] = useState<MovementPattern[]>([]);
  const [selectedLoadingTypes, setSelectedLoadingTypes] = useState<LoadingType[]>([]);
  const [selectedLateralities, setSelectedLateralities] = useState<Laterality[]>([]);
  const [minimumLoadability, setMinimumLoadability] = useState("");
  const [selectedVelocities, setSelectedVelocities] = useState<VelocityCharacteristic[]>([]);
  const [maximumSkillComplexity, setMaximumSkillComplexity] = useState("");
  const [maximumImpactLevel, setMaximumImpactLevel] = useState("");
  const [maximumStabilityDemand, setMaximumStabilityDemand] = useState("");
  const [maximumFatigueCost, setMaximumFatigueCost] = useState("");
  const [maximumSorenessCost, setMaximumSorenessCost] = useState("");
  const [requiresOutdoorAccess, setRequiresOutdoorAccess] = useState(false);
  const [minimumFloorArea, setMinimumFloorArea] = useState("");
  const [contraindicationTags, setContraindicationTags] = useState("");
  const [observationIds, setObservationIds] = useState<string[]>([]);
  const [evidenceIds, setEvidenceIds] = useState<string[]>([]);
  const [stimulusRationale, setStimulusRationale] = useState("");
  const [minimumMinutes, setMinimumMinutes] = useState("");
  const [targetMinutes, setTargetMinutes] = useState("");
  const [sessionsPerWeek, setSessionsPerWeek] = useState("");
  const [demandRationale, setDemandRationale] = useState("");
  const [demandVersion, setDemandVersion] = useState("");
  const [applicabilityRationale, setApplicabilityRationale] = useState("");
  const [uncertainty, setUncertainty] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<ResourceDemandPreparationResult | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!confirmed) return;
    setBusy(true);
    setMessage("");
    try {
      const common = {
        prepared_at: new Date().toISOString(),
        demand_rationale: demandRationale,
        demand_version: demandVersion,
        applicability_rationale: applicabilityRationale,
        uncertainty,
      };
      let request: OperatorResourceDemandRequest;
      if (deferred) {
        request = {
          ...common,
          mode: "deferred",
          source_observation_ids: observationIds,
          evidence_claim_ids: evidenceIds,
        };
      } else {
        const floorArea = minimumFloorArea.trim() ? Number(minimumFloorArea) : null;
        if (floorArea !== null && (!Number.isFinite(floorArea) || floorArea <= 0)) {
          throw new Error("Minimum floor area must be a positive number when supplied.");
        }
        request = {
          ...common,
          mode: "active",
          environment_id: environmentId,
          exercise_candidate_ids: exerciseCandidateIds,
          exercise_resolver_policy_id: resolverPolicyId,
          stimulus_specification: {
            movement_patterns: selectedMovementPatterns,
            allowed_loading_types: selectedLoadingTypes,
            allowed_lateralities: selectedLateralities,
            minimum_loadability: minimumLoadability as Loadability,
            required_velocity_characteristics: selectedVelocities,
            maximum_skill_complexity: maximumSkillComplexity as CostLevel,
            maximum_impact_level: maximumImpactLevel as ImpactLevel,
            maximum_stability_demand: maximumStabilityDemand as CostLevel,
            maximum_fatigue_cost: maximumFatigueCost as CostLevel,
            maximum_soreness_cost: maximumSorenessCost as CostLevel,
            requires_outdoor_access: requiresOutdoorAccess,
            minimum_floor_area_m2: floorArea,
            contraindication_tags: contraindicationTags
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean),
            source_observation_ids: observationIds,
            evidence_claim_ids: evidenceIds,
            rationale: stimulusRationale,
          },
          minimum_weekly_minutes: positiveInteger(minimumMinutes, "Minimum weekly minutes"),
          target_weekly_minutes: positiveInteger(targetMinutes, "Target weekly minutes"),
          sessions_per_week: positiveInteger(sessionsPerWeek, "Sessions per week"),
        };
      }
      setResult(
        await submitResourceDemand(
          apiBaseUrl,
          projection.strategy.id,
          priorityOption.priority.id,
          request,
        ),
      );
      await onCreated();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to prepare the resource demand.");
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return <ResourceDemandReceipt result={result} strategyId={projection.strategy.id} />;
  }

  return (
    <form className="governed-context resource-demand-form" onSubmit={submit}>
      <header>
        <div>
          <p className="eyebrow">Priority #{priorityOption.priority.rank} · {priorityOption.priority.state}</p>
          <h2>{priorityOption.adaptation.name}</h2>
          <p>
            {deferred
              ? "Record why this priority intentionally receives zero training resource."
              : "Define the required stimulus first, then ask the deterministic resolver what this environment can reproduce."}
          </p>
        </div>
        <span className="status-badge">{priorityOption.demand_history.length} historical demand(s)</span>
      </header>

      {!deferred ? (
        <>
          <section className="resource-section">
            <h3>1. Environment and resolver authority</h3>
            <div className="context-selects">
              <label>
                Environment
                <select value={environmentId} onChange={(event) => setEnvironmentId(event.target.value)} required>
                  <option value="" disabled>Select an exact environment snapshot</option>
                  {projection.environments.map(({ environment, snapshot }) => (
                    <option key={environment.id} value={environment.id}>
                      {environment.name} · {snapshot.available_equipment.length} available item(s)
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Resolver policy
                <select value={resolverPolicyId} onChange={(event) => setResolverPolicyId(event.target.value)} required>
                  <option value="" disabled>Select a versioned resolver policy</option>
                  {projection.exercise_resolver_policies.map((policy) => (
                    <option key={policy.id} value={policy.id}>{policy.policy_version}</option>
                  ))}
                </select>
              </label>
            </div>
            {environmentId ? (
              <div className="resource-environment-detail">
                {projection.environments
                  .filter(({ environment }) => environment.id === environmentId)
                  .map(({ environment, snapshot }) => (
                    <div key={environment.id}>
                      <strong>{environment.name}</strong>
                      <span>
                        Floor {snapshot.floor_area_m2 ?? "unknown"} m² · noise {snapshot.max_noise_level} · outdoor {snapshot.outdoor_access ? "yes" : "no"}
                      </span>
                      <ul>
                        {snapshot.available_equipment.map((item) => (
                          <li key={item.equipment_id}>{item.category} · {item.equipment_id}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
              </div>
            ) : null}
          </section>

          <section className="resource-section">
            <h3>2. Explicit stimulus specification</h3>
            <MultiCheck legend="Movement patterns" values={movementPatterns} selected={selectedMovementPatterns} onChange={setSelectedMovementPatterns} />
            <MultiCheck legend="Allowed loading types" values={loadingTypes} selected={selectedLoadingTypes} onChange={setSelectedLoadingTypes} />
            <MultiCheck legend="Allowed lateralities" values={lateralities} selected={selectedLateralities} onChange={setSelectedLateralities} />
            <MultiCheck legend="Required velocity characteristics (optional)" values={velocityCharacteristics} selected={selectedVelocities} onChange={setSelectedVelocities} />
            <div className="resource-ceilings">
              <label>Minimum loadability<select value={minimumLoadability} onChange={(event) => setMinimumLoadability(event.target.value)} required><option value="" disabled>Select</option>{loadabilities.map((value) => <option key={value}>{value}</option>)}</select></label>
              <label>Maximum skill complexity<select value={maximumSkillComplexity} onChange={(event) => setMaximumSkillComplexity(event.target.value)} required><option value="" disabled>Select</option>{costLevels.map((value) => <option key={value}>{value}</option>)}</select></label>
              <label>Maximum impact<select value={maximumImpactLevel} onChange={(event) => setMaximumImpactLevel(event.target.value)} required><option value="" disabled>Select</option>{impactLevels.map((value) => <option key={value}>{value}</option>)}</select></label>
              <label>Maximum stability demand<select value={maximumStabilityDemand} onChange={(event) => setMaximumStabilityDemand(event.target.value)} required><option value="" disabled>Select</option>{costLevels.map((value) => <option key={value}>{value}</option>)}</select></label>
              <label>Maximum fatigue cost<select value={maximumFatigueCost} onChange={(event) => setMaximumFatigueCost(event.target.value)} required><option value="" disabled>Select</option>{costLevels.map((value) => <option key={value}>{value}</option>)}</select></label>
              <label>Maximum soreness cost<select value={maximumSorenessCost} onChange={(event) => setMaximumSorenessCost(event.target.value)} required><option value="" disabled>Select</option>{costLevels.map((value) => <option key={value}>{value}</option>)}</select></label>
              <label>Minimum floor area m² (optional)<input type="number" min="0.1" step="0.1" value={minimumFloorArea} onChange={(event) => setMinimumFloorArea(event.target.value)} /></label>
              <label>Contraindication tags (comma-separated)<input value={contraindicationTags} onChange={(event) => setContraindicationTags(event.target.value)} /></label>
            </div>
            <label className="context-confirmation">
              <input type="checkbox" checked={requiresOutdoorAccess} onChange={(event) => setRequiresOutdoorAccess(event.target.checked)} />
              <span>This stimulus requires outdoor access.</span>
            </label>
            <label>
              Stimulus rationale
              <textarea value={stimulusRationale} onChange={(event) => setStimulusRationale(event.target.value)} rows={4} required />
            </label>
          </section>

          <section className="resource-section">
            <h3>3. Explicit exercise candidate set</h3>
            <p className="form-help">
              The full catalog remains visible. Ontology role is descriptive; no exercise is preselected or promised equivalent.
            </p>
            <div className="resource-exercise-grid">
              {projection.exercise_catalog.map((exercise) => {
                const role = exercise.primary_adaptation_ids.includes(priorityOption.adaptation.id)
                  ? "primary"
                  : exercise.secondary_adaptation_ids.includes(priorityOption.adaptation.id)
                    ? "secondary"
                    : "unlinked";
                return (
                  <label key={exercise.id}>
                    <input
                      type="checkbox"
                      checked={exerciseCandidateIds.includes(exercise.id)}
                      onChange={(event) => setExerciseCandidateIds(toggle(exerciseCandidateIds, exercise.id, event.target.checked))}
                    />
                    <span>
                      <strong>{exercise.name}</strong>
                      <small>{role} adaptation metadata · {label(exercise.loading_type)} · {exercise.loadability} loadability</small>
                      <small>{exercise.movement_patterns.map(label).join(", ")}</small>
                    </span>
                  </label>
                );
              })}
            </div>
          </section>
        </>
      ) : null}

      <ProvenanceSelector
        observations={projection.source_observations}
        evidenceClaims={projection.evidence_claims}
        selectedObservationIds={observationIds}
        selectedEvidenceIds={evidenceIds}
        onObservationsChange={setObservationIds}
        onEvidenceChange={setEvidenceIds}
      />

      <section className="resource-section">
        <h3>{deferred ? "Zero-resource decision" : "4. Weekly resource demand"}</h3>
        {!deferred ? (
          <div className="resource-ceilings">
            <label>Minimum weekly minutes<input type="number" min="1" value={minimumMinutes} onChange={(event) => setMinimumMinutes(event.target.value)} required /></label>
            <label>Target weekly minutes<input type="number" min="1" value={targetMinutes} onChange={(event) => setTargetMinutes(event.target.value)} required /></label>
            <label>Sessions per week<input type="number" min="1" value={sessionsPerWeek} onChange={(event) => setSessionsPerWeek(event.target.value)} required /></label>
          </div>
        ) : (
          <p className="review-existing-strategy">
            DEFER is recorded as zero minutes, zero sessions, and no stimulus or exercise resolution.
          </p>
        )}
        <div className="context-review-fields">
          <label>Demand rationale<textarea value={demandRationale} onChange={(event) => setDemandRationale(event.target.value)} rows={4} required /></label>
          <label>Demand version<input value={demandVersion} onChange={(event) => setDemandVersion(event.target.value)} placeholder="reviewed-demand@1.0.0" required /></label>
          <label>Applicability rationale<textarea value={applicabilityRationale} onChange={(event) => setApplicabilityRationale(event.target.value)} rows={4} required /></label>
          <label>Known uncertainty<textarea value={uncertainty} onChange={(event) => setUncertainty(event.target.value)} rows={4} required /></label>
        </div>
      </section>

      <label className="context-confirmation">
        <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
        <span>
          I reviewed every selected stimulus, candidate, environment, resource, provenance, rationale,
          and uncertainty field. I understand that partial or infeasible resolution may be correct.
        </span>
      </label>
      <button type="submit" className="primary-button" disabled={!confirmed || busy}>
        {busy ? "Resolving and recording…" : deferred ? "Record deferred demand" : "Resolve and record demand"}
      </button>
      <p className="form-help">This appends history. It does not create a block, week, session, or workout.</p>
      {message ? <p className="form-error" role="alert">{message}</p> : null}
    </form>
  );
}

export function ResourceDemandReviewClient({ initialStrategyId }: { initialStrategyId: string }) {
  const [strategyId, setStrategyId] = useState(initialStrategyId);
  const [projection, setProjection] = useState<ResourceDemandPreparationProjection | null>(null);
  const [priorityId, setPriorityId] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function loadProjection() {
    const normalized = strategyId.trim();
    setMessage("");
    setProjection(null);
    setPriorityId("");
    if (!uuidPattern.test(normalized)) {
      setMessage("Enter a valid strategy UUID.");
      return;
    }
    setBusy(true);
    try {
      setProjection(await fetchResourceDemandPreparation(apiBaseUrl, normalized));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load resource-demand preparation.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshProjection() {
    setProjection(await fetchResourceDemandPreparation(apiBaseUrl, strategyId.trim()));
  }

  const selected = projection?.priorities.find(({ priority }) => priority.id === priorityId);

  return (
    <main className="review-shell">
      <header className="review-topbar">
        <div>
          <p className="eyebrow">AGAS · Strategy to stimulus</p>
          <h1>Resource-demand review</h1>
          <p>
            Translate one immutable strategy priority into an explicit stimulus, honest environment
            resolution, and reviewed weekly resource demand.
          </p>
        </div>
        <nav className="review-route-links" aria-label="Reviewer routes">
          <Link href="/review/queue" className="text-link">Queue</Link>
          <Link href="/review" className="text-link">Initial strategy</Link>
          <Link href="/review/blocks" className="text-link">Blocks</Link>
          <Link href="/review/post-block" className="text-link">Post-block</Link>
          <Link href="/" className="text-link">Athlete PWA</Link>
        </nav>
      </header>
      <aside className="review-boundary">
        <strong>No training values are inferred here.</strong>
        <span>
          Every material field begins blank. The server owns reviewer identity, and the deterministic
          resolver may return full, partial, or infeasible without silently changing the priority.
        </span>
      </aside>
      <section className="review-input resource-strategy-loader">
        <label htmlFor="resource-strategy-id">Long-range strategy ID</label>
        <input id="resource-strategy-id" value={strategyId} onChange={(event) => setStrategyId(event.target.value)} placeholder="00000000-0000-4000-8000-000000000000" />
        <button type="button" className="primary-button" disabled={busy} onClick={() => void loadProjection()}>
          {busy ? "Loading exact inputs…" : "Load strategy preparation"}
        </button>
      </section>
      {message ? <p className="form-error review-message" role="alert">{message}</p> : null}
      {projection ? (
        <>
          <section className="review-preparation resource-strategy-summary">
            <header>
              <div>
                <p className="eyebrow">Persisted strategy</p>
                <h2>Select one immutable priority</h2>
                <p>{projection.strategy.block_hypothesis}</p>
                <code>{projection.strategy.id}</code>
              </div>
              <span className="status-badge">{projection.priorities.length} priority state(s)</span>
            </header>
            <div className="resource-priority-grid">
              {projection.priorities.map((option) => (
                <button
                  key={option.priority.id}
                  type="button"
                  className={priorityId === option.priority.id ? "resource-priority resource-priority--selected" : "resource-priority"}
                  onClick={() => setPriorityId(option.priority.id)}
                >
                  <span>#{option.priority.rank} · {option.priority.state}</span>
                  <strong>{option.adaptation.name}</strong>
                  <small>{label(option.adaptation.domain)}</small>
                  <small>{option.demand_history.length} historical demand(s)</small>
                </button>
              ))}
            </div>
            {projection.priorities.some((option) => option.demand_history.length > 0) ? (
              <details>
                <summary>Inspect immutable demand history</summary>
                <div className="resource-history">
                  {projection.priorities.flatMap((option) =>
                    option.demand_history.map((history) => (
                      <article key={history.resource_demand.id}>
                        <strong>{option.adaptation.name} · {history.exercise_resolution?.status ?? "deferred"}</strong>
                        <code>{history.resource_demand.id}</code>
                        <span>{history.resource_demand.minimum_weekly_minutes}–{history.resource_demand.target_weekly_minutes} min · {history.resource_demand.sessions_per_week} session(s)</span>
                        <p>{history.resource_demand.rationale}</p>
                      </article>
                    )),
                  )}
                </div>
              </details>
            ) : null}
          </section>
          {selected ? (
            <ResourceDemandEditor
              key={selected.priority.id}
              projection={projection}
              priorityOption={selected}
              onCreated={refreshProjection}
            />
          ) : (
            <p className="form-help resource-selection-help">Choose a priority to author one explicit demand.</p>
          )}
        </>
      ) : null}
    </main>
  );
}
