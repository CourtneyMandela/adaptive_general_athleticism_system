"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import {
  buildAthleteOnboardingCommand,
  fetchOnboardingEquipment,
  submitAthleteOnboarding,
  type OnboardingEnvironmentInput,
  type OnboardingEquipmentOption,
} from "@/lib/onboarding";
import type { Confidence } from "@/lib/current-week";

interface EnvironmentDraft extends OnboardingEnvironmentInput {
  key: string;
}

function blankEnvironment(index: number): EnvironmentDraft {
  return {
    key: `environment-${index}`,
    name: index === 0 ? "Home" : "",
    floorAreaM2: null,
    noiseConstraints: null,
    maxNoiseLevel: "moderate",
    outdoorAccess: false,
    equipmentIds: [],
  };
}

function splitEntries(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function OnboardingForm({
  apiBaseUrl,
  onCreated,
}: {
  apiBaseUrl: string;
  onCreated: (athleteId: string) => void;
}) {
  const [displayName, setDisplayName] = useState("");
  const [goals, setGoals] = useState("");
  const [preferredActivities, setPreferredActivities] = useState("");
  const [dislikedActivities, setDislikedActivities] = useState("");
  const [environments, setEnvironments] = useState<EnvironmentDraft[]>([
    blankEnvironment(0),
  ]);
  const [reliability, setReliability] = useState<Confidence>("moderate");
  const [equipment, setEquipment] = useState<OnboardingEquipmentOption[]>([]);
  const [catalogState, setCatalogState] = useState<"loading" | "ready" | "error">("loading");
  const [state, setState] = useState<"idle" | "saving" | "error">("idle");
  const [message, setMessage] = useState("");
  const nextEnvironmentKey = useRef(1);

  useEffect(() => {
    let active = true;
    void fetchOnboardingEquipment(apiBaseUrl)
      .then((result) => {
        if (active) {
          setEquipment(result);
          setCatalogState("ready");
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(error instanceof Error ? error.message : "Unable to load equipment.");
          setCatalogState("error");
        }
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl]);

  function updateEnvironment(key: string, update: Partial<EnvironmentDraft>) {
    setEnvironments((current) =>
      current.map((environment) =>
        environment.key === key ? { ...environment, ...update } : environment,
      ),
    );
  }

  function toggleEquipment(environment: EnvironmentDraft, equipmentId: string) {
    const selected = environment.equipmentIds.includes(equipmentId);
    updateEnvironment(environment.key, {
      equipmentIds: selected
        ? environment.equipmentIds.filter((id) => id !== equipmentId)
        : [...environment.equipmentIds, equipmentId],
    });
  }

  function addEnvironment() {
    const key = nextEnvironmentKey.current;
    nextEnvironmentKey.current += 1;
    setEnvironments((current) => [
      ...current,
      { ...blankEnvironment(current.length), key: `environment-${key}` },
    ]);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("saving");
    setMessage("");
    try {
      const command = buildAthleteOnboardingCommand({
        displayName,
        goals: splitEntries(goals),
        preferredActivities: splitEntries(preferredActivities),
        dislikedActivities: splitEntries(dislikedActivities),
        environments,
        reliability,
      });
      const result = await submitAthleteOnboarding(apiBaseUrl, command);
      onCreated(result.athlete.id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to create the profile.");
      setState("error");
    }
  }

  return (
    <form className="onboarding-form" onSubmit={submit}>
      <div className="form-section">
        <div>
          <p className="eyebrow">Profile</p>
          <h2>Start with what you know.</h2>
        </div>
        <label>
          Display name
          <input
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            autoComplete="name"
            required
          />
        </label>
        <label>
          Training goals
          <textarea
            value={goals}
            onChange={(event) => setGoals(event.target.value)}
            placeholder="One goal per line"
            rows={3}
            required
          />
        </label>
        <div className="paired-fields">
          <label>
            Activities you enjoy <span>optional</span>
            <textarea
              value={preferredActivities}
              onChange={(event) => setPreferredActivities(event.target.value)}
              placeholder="Hiking, cycling"
              rows={2}
            />
          </label>
          <label>
            Activities you avoid <span>optional</span>
            <textarea
              value={dislikedActivities}
              onChange={(event) => setDislikedActivities(event.target.value)}
              placeholder="Long treadmill sessions"
              rows={2}
            />
          </label>
        </div>
      </div>

      <div className="form-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Environment</p>
            <h2>Where can you train?</h2>
          </div>
          <button
            type="button"
            className="secondary-button"
            onClick={addEnvironment}
          >
            Add another
          </button>
        </div>
        {environments.map((environment, index) => (
          <fieldset className="environment-editor" key={environment.key}>
            <legend>Environment {index + 1}</legend>
            {environments.length > 1 ? (
              <button
                type="button"
                className="remove-button"
                onClick={() =>
                  setEnvironments((current) =>
                    current.filter((item) => item.key !== environment.key),
                  )
                }
              >
                Remove
              </button>
            ) : null}
            <div className="paired-fields">
              <label>
                Name
                <input
                  value={environment.name}
                  onChange={(event) =>
                    updateEnvironment(environment.key, { name: event.target.value })
                  }
                  placeholder="Home, gym, office"
                  required
                />
              </label>
              <label>
                Usable floor area, m² <span>optional</span>
                <input
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={environment.floorAreaM2 ?? ""}
                  onChange={(event) =>
                    updateEnvironment(environment.key, {
                      floorAreaM2: event.target.value ? Number(event.target.value) : null,
                    })
                  }
                />
              </label>
              <label>
                Maximum noise
                <select
                  value={environment.maxNoiseLevel}
                  onChange={(event) =>
                    updateEnvironment(environment.key, {
                      maxNoiseLevel: event.target.value as EnvironmentDraft["maxNoiseLevel"],
                    })
                  }
                >
                  <option value="low">Low</option>
                  <option value="moderate">Moderate</option>
                  <option value="high">High</option>
                </select>
              </label>
              <label>
                Noise constraints <span>optional</span>
                <input
                  value={environment.noiseConstraints ?? ""}
                  onChange={(event) =>
                    updateEnvironment(environment.key, {
                      noiseConstraints: event.target.value || null,
                    })
                  }
                  placeholder="Quiet after 8 PM"
                />
              </label>
            </div>
            <label className="inline-check">
              <input
                type="checkbox"
                checked={environment.outdoorAccess}
                onChange={(event) =>
                  updateEnvironment(environment.key, { outdoorAccess: event.target.checked })
                }
              />
              Outdoor training is available here
            </label>
            <div>
              <span className="field-label">Available equipment</span>
              {catalogState === "loading" ? (
                <p className="form-help">Loading the controlled equipment catalog…</p>
              ) : equipment.length ? (
                <div className="equipment-options">
                  {equipment.map((item) => (
                    <label key={item.equipment_id}>
                      <input
                        type="checkbox"
                        checked={environment.equipmentIds.includes(item.equipment_id)}
                        onChange={() => toggleEquipment(environment, item.equipment_id)}
                      />
                      <span>
                        <strong>{item.name}</strong>
                        <small>{item.category.replaceAll("_", " ")}</small>
                      </span>
                    </label>
                  ))}
                </div>
              ) : (
                <p className="form-help">
                  No seeded equipment is available. You can still save the environment.
                </p>
              )}
            </div>
          </fieldset>
        ))}
      </div>

      <div className="form-section compact-section">
        <label>
          How certain are you about this information?
          <select
            value={reliability}
            onChange={(event) => setReliability(event.target.value as Confidence)}
          >
            <option value="moderate">Reasonably certain</option>
            <option value="high">Very certain</option>
            <option value="low">Some details are uncertain</option>
            <option value="unknown">Unknown</option>
          </select>
        </label>
        <p className="form-help">
          This saves your report with its timestamp and source. It does not infer fitness scores,
          prescribe workouts, or collect health and injury information.
        </p>
      </div>

      <button type="submit" className="primary-button" disabled={state === "saving"}>
        {state === "saving" ? "Saving profile…" : "Create profile"}
      </button>
      {message ? <p className="form-error" role="alert">{message}</p> : null}
    </form>
  );
}
