"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import type { Confidence } from "@/lib/current-week";
import {
  buildEquipmentStateReportCommand,
  fetchAthleteEnvironments,
  submitEquipmentStateReport,
  type AthleteEnvironmentProjection,
  type EquipmentState,
} from "@/lib/environment";

type ChangeChoice = "no_change" | "available" | "unavailable";

function localDateTime(value = new Date()): string {
  const local = new Date(value.getTime() - value.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function stateLabel(state: EquipmentState): string {
  return state === "unknown" ? "Not reported" : state;
}

export function EnvironmentPanel({
  apiBaseUrl,
  athleteId,
}: {
  apiBaseUrl: string;
  athleteId: string;
}) {
  const [projection, setProjection] = useState<AthleteEnvironmentProjection | null>(null);
  const [environmentId, setEnvironmentId] = useState("");
  const [changes, setChanges] = useState<Record<string, ChangeChoice>>({});
  const [effectiveFrom, setEffectiveFrom] = useState(localDateTime);
  const [effectiveUntil, setEffectiveUntil] = useState("");
  const [reason, setReason] = useState("");
  const [reliability, setReliability] = useState<Confidence>("moderate");
  const [state, setState] = useState<"loading" | "ready" | "saving" | "error">("loading");
  const [message, setMessage] = useState("");

  const reload = useCallback(async () => {
    setState("loading");
    setMessage("");
    try {
      const result = await fetchAthleteEnvironments(apiBaseUrl, athleteId);
      setProjection(result);
      setEnvironmentId((current) =>
        result.environments.some((item) => item.environment_id === current)
          ? current
          : (result.environments[0]?.environment_id ?? ""),
      );
      setState("ready");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load environments.");
      setState("error");
    }
  }, [apiBaseUrl, athleteId]);

  useEffect(() => {
    let active = true;
    void fetchAthleteEnvironments(apiBaseUrl, athleteId)
      .then((result) => {
        if (active) {
          setProjection(result);
          setEnvironmentId(result.environments[0]?.environment_id ?? "");
          setState("ready");
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(error instanceof Error ? error.message : "Unable to load environments.");
          setState("error");
        }
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl, athleteId]);

  const environment = projection?.environments.find(
    (item) => item.environment_id === environmentId,
  );

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!environment) return;
    setState("saving");
    setMessage("");
    try {
      const command = buildEquipmentStateReportCommand({
        changes: environment.equipment
          .filter((item) => (changes[item.equipment_id] ?? "no_change") !== "no_change")
          .map((item) => ({
            equipmentId: item.equipment_id,
            isAvailable: changes[item.equipment_id] === "available",
            effectiveFrom: new Date(effectiveFrom),
            effectiveUntil: effectiveUntil ? new Date(effectiveUntil) : null,
            reason: reason || null,
          })),
        reliability,
        reportReason: reason,
      });
      await submitEquipmentStateReport(
        apiBaseUrl,
        athleteId,
        environment.environment_id,
        command,
      );
      setChanges({});
      setEffectiveUntil("");
      await reload();
      setMessage("Equipment history recorded. Existing sessions were not silently rewritten.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to record equipment state.");
      setState("error");
    }
  }

  const changeCount = Object.values(changes).filter((item) => item !== "no_change").length;

  return (
    <section className="environment-panel" aria-labelledby="environment-title">
      <header className="environment-panel__heading">
        <div>
          <p className="eyebrow">Training environments</p>
          <h2 id="environment-title">What is actually available?</h2>
        </div>
        <button type="button" className="text-button" onClick={() => void reload()} disabled={state === "loading" || state === "saving"}>
          {state === "loading" ? "Loading…" : "Refresh"}
        </button>
      </header>
      <p className="assessment-message">
        Record only what changed. Unlisted equipment keeps its current or unknown state, and a
        temporary report can expire without erasing earlier history.
      </p>
      {projection?.environments.length ? (
        <>
          <label className="environment-selector">
            Environment
            <select
              value={environmentId}
              onChange={(event) => {
                setEnvironmentId(event.target.value);
                setChanges({});
              }}
            >
              {projection.environments.map((item) => (
                <option value={item.environment_id} key={item.environment_id}>{item.name}</option>
              ))}
            </select>
          </label>
          {environment ? (
            <>
              <dl className="environment-constraints">
                <div><dt>Space</dt><dd>{environment.floor_area_m2 ? `${environment.floor_area_m2} m²` : "Not specified"}</dd></div>
                <div><dt>Noise</dt><dd>{environment.max_noise_level}</dd></div>
                <div><dt>Outdoor access</dt><dd>{environment.outdoor_access ? "Available" : "Not reported"}</dd></div>
              </dl>
              <form className="equipment-change-form" onSubmit={submit}>
                <div className="equipment-state-list">
                  {environment.equipment.map((item) => (
                    <label key={item.equipment_id}>
                      <span>
                        <strong>{item.name}</strong>
                        <small>{item.category.replaceAll("_", " ")} · {stateLabel(item.state)}</small>
                      </span>
                      <select
                        value={changes[item.equipment_id] ?? "no_change"}
                        onChange={(event) =>
                          setChanges((current) => ({
                            ...current,
                            [item.equipment_id]: event.target.value as ChangeChoice,
                          }))
                        }
                      >
                        <option value="no_change">No change</option>
                        <option value="available">Available</option>
                        <option value="unavailable">Unavailable</option>
                      </select>
                    </label>
                  ))}
                </div>
                <div className="equipment-change-timing">
                  <label>
                    Effective from
                    <input type="datetime-local" required value={effectiveFrom} onChange={(event) => setEffectiveFrom(event.target.value)} />
                  </label>
                  <label>
                    Temporary state ends
                    <input type="datetime-local" value={effectiveUntil} onChange={(event) => setEffectiveUntil(event.target.value)} />
                  </label>
                </div>
                <label>
                  Reason for this report
                  <input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Travel, new equipment, temporary outage…" required />
                </label>
                <label>
                  Confidence in this report
                  <select value={reliability} onChange={(event) => setReliability(event.target.value as Confidence)}>
                    <option value="high">High</option>
                    <option value="moderate">Moderate</option>
                    <option value="low">Low</option>
                    <option value="unknown">Unknown</option>
                  </select>
                </label>
                <button type="submit" disabled={state === "saving" || changeCount === 0}>
                  {state === "saving"
                    ? "Recording…"
                    : changeCount
                      ? `Record ${changeCount} change${changeCount === 1 ? "" : "s"}`
                      : "Choose equipment changes"}
                </button>
                <p className="form-help">
                  This records environmental state. It does not claim a substitute is equivalent or
                  alter an immutable workout; reviewed exercise re-resolution is a separate step.
                </p>
              </form>
            </>
          ) : null}
        </>
      ) : state === "loading" ? (
        <p className="form-help">Loading owned environments…</p>
      ) : (
        <p className="dashboard-empty">No persisted environment is available.</p>
      )}
      {message ? <p className={state === "error" ? "form-error" : "form-help"} role={state === "error" ? "alert" : undefined}>{message}</p> : null}
    </section>
  );
}
