"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  buildWeeklyAvailabilityConfirmationCommand,
  buildWeeklyRollForwardCommand,
  submitWeeklyAvailabilityConfirmation,
  submitWeeklyRollForward,
  type Confidence,
  type WeekProjection,
  type WeeklyAvailabilityDraft,
} from "@/lib/current-week";
import { fetchAthleteEnvironments } from "@/lib/environment";

interface EditableAvailabilityWindow {
  environmentId: string;
  environmentName: string;
  startsAt: string;
  endsAt: string;
}

function addDaysForLocalInput(value: string, days: number): string {
  const instant = new Date(value);
  instant.setDate(instant.getDate() + days);
  const local = new Date(instant.getTime() - instant.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function initialWindows(week: WeekProjection): EditableAvailabilityWindow[] {
  return week.availability.windows.map((window) => ({
    environmentId: window.environment_id,
    environmentName: window.environment_name,
    startsAt: addDaysForLocalInput(window.starts_at, 7),
    endsAt: addDaysForLocalInput(window.ends_at, 7),
  }));
}

function reviewTitle(status: WeekProjection["review"]["status"]): string {
  const titles = {
    awaiting_sessions: "Finish recording this week",
    awaiting_post_session_safety: "Close the recovery reports",
    awaiting_progression: "Resolve progression decisions",
    manual_configuration_required: "A governed review is required",
    ready_to_prepare_next_week: "Confirm next week’s availability",
    environment_revision_required: "Environment review is required",
    ready_to_finalize_next_week: "Next week is ready to finalize",
    next_week_already_prepared: "Next week is ready",
    block_complete: "This training block is complete",
  };
  return titles[status];
}

export function WeeklyReview({
  week,
  apiBaseUrl,
  athleteId,
  onWeekUpdated,
  onWeekPrepared,
}: {
  week: WeekProjection;
  apiBaseUrl: string;
  athleteId: string;
  onWeekUpdated: () => Promise<void>;
  onWeekPrepared: (nextWeekStart: string) => Promise<void>;
}) {
  const [windows, setWindows] = useState(() => initialWindows(week));
  const [environmentOptions, setEnvironmentOptions] = useState(() =>
    Array.from(
      new Map(
        week.availability.windows.map((window) => [
          window.environment_id,
          { id: window.environment_id, name: window.environment_name },
        ]),
      ).values(),
    ),
  );
  const [reliability, setReliability] = useState<Confidence>("moderate");
  const [confirmed, setConfirmed] = useState(false);
  const [state, setState] = useState<"idle" | "saving" | "error">("idle");
  const [message, setMessage] = useState("");
  const outcomeSummary = useMemo(
    () => {
      const outcomes: Array<readonly [string, number]> = [
        ["Progress", week.review.progression_outcomes.progress],
        ["Repeat", week.review.progression_outcomes.repeat],
        ["Hold", week.review.progression_outcomes.hold],
        ["Review", week.review.progression_outcomes.review_required],
      ];
      return outcomes.filter(([, count]) => count > 0);
    },
    [week.review.progression_outcomes],
  );

  useEffect(() => {
    let active = true;
    void fetchAthleteEnvironments(apiBaseUrl, athleteId)
      .then((result) => {
        if (active && result.environments.length) {
          setEnvironmentOptions(
            result.environments.map((environment) => ({
              id: environment.environment_id,
              name: environment.name,
            })),
          );
        }
      })
      .catch(() => {
        // The source-week environments remain valid fallback choices.
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl, athleteId]);

  function updateWindow(index: number, field: "startsAt" | "endsAt", value: string) {
    setWindows((current) =>
      current.map((window, windowIndex) =>
        windowIndex === index ? { ...window, [field]: value } : window,
      ),
    );
  }

  function updateEnvironment(index: number, environmentId: string) {
    const option = environmentOptions.find((item) => item.id === environmentId);
    if (!option) return;
    setWindows((current) =>
      current.map((window, windowIndex) =>
        windowIndex === index
          ? { ...window, environmentId: option.id, environmentName: option.name }
          : window,
      ),
    );
  }

  async function confirmNextWeekAvailability(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!confirmed || week.review.next_week_start === null) return;
    setState("saving");
    setMessage("");
    try {
      const availability: WeeklyAvailabilityDraft[] = windows.map((window) => ({
        environmentId: window.environmentId,
        startsAt: new Date(window.startsAt),
        endsAt: new Date(window.endsAt),
      }));
      const command = buildWeeklyAvailabilityConfirmationCommand({
        windows: availability,
        reliability,
      });
      await submitWeeklyAvailabilityConfirmation(apiBaseUrl, week.weekly_plan_id, command);
      await onWeekUpdated();
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Unable to confirm availability.");
    }
  }

  async function finalizeNextWeek() {
    const availability = week.review.confirmed_availability;
    if (availability === null || week.review.next_week_start === null) return;
    setState("saving");
    setMessage("");
    try {
      const command = buildWeeklyRollForwardCommand({
        weeklyAvailabilityId: availability.weekly_availability_id,
      });
      await submitWeeklyRollForward(apiBaseUrl, week.weekly_plan_id, command);
      await onWeekPrepared(week.review.next_week_start);
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Unable to finalize the next week.");
    }
  }

  return (
    <section className="weekly-review" aria-labelledby="weekly-review-title">
      <div className="weekly-review__heading">
        <div>
          <p className="eyebrow">Weekly review</p>
          <h2 id="weekly-review-title">{reviewTitle(week.review.status)}</h2>
          <p>{week.review.reason}</p>
        </div>
        <dl className="review-counts">
          <div>
            <dt>Sessions recorded</dt>
            <dd>
              {week.review.recorded_sessions}/{week.review.scheduled_sessions}
            </dd>
          </div>
          <div>
            <dt>Recovery reports</dt>
            <dd>
              {week.review.post_session_closed}/{week.review.recorded_sessions}
            </dd>
          </div>
          <div>
            <dt>Progressions resolved</dt>
            <dd>
              {week.review.resolved_progression_items}/{week.review.progression_items}
            </dd>
          </div>
        </dl>
      </div>

      {outcomeSummary.length ? (
        <ul className="review-outcomes" aria-label="Recorded progression outcomes">
          {outcomeSummary.map(([label, count]) => (
            <li key={label}>
              <strong>{count}</strong> {label}
            </li>
          ))}
        </ul>
      ) : null}

      {week.review.status === "ready_to_prepare_next_week" ? (
        <form className="availability-form" onSubmit={confirmNextWeekAvailability}>
          <fieldset disabled={state === "saving"}>
            <legend>Availability for the week of {week.review.next_week_start}</legend>
            <p className="form-help">
              These windows start as a seven-day shift of this week. Confirm the actual places and
              times; the saved report becomes provenance for the next plan.
            </p>
            <div className="availability-windows">
              {windows.map((window, index) => (
                <section className="availability-window" key={`${window.environmentId}-${index}`}>
                  <label>
                    Training environment
                    <select
                      value={window.environmentId}
                      onChange={(event) => updateEnvironment(index, event.target.value)}
                    >
                      {environmentOptions.map((environment) => (
                        <option value={environment.id} key={environment.id}>
                          {environment.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="availability-fields">
                    <label>
                      Starts
                      <input
                        type="datetime-local"
                        required
                        value={window.startsAt}
                        onChange={(event) => updateWindow(index, "startsAt", event.target.value)}
                      />
                    </label>
                    <label>
                      Ends
                      <input
                        type="datetime-local"
                        required
                        value={window.endsAt}
                        onChange={(event) => updateWindow(index, "endsAt", event.target.value)}
                      />
                    </label>
                  </div>
                </section>
              ))}
            </div>
            <label>
              Confidence in this availability report
              <select
                value={reliability}
                onChange={(event) => setReliability(event.target.value as Confidence)}
              >
                <option value="high">High</option>
                <option value="moderate">Moderate</option>
                <option value="low">Low</option>
                <option value="unknown">Unknown</option>
              </select>
            </label>
            <label className="availability-confirmation">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(event) => setConfirmed(event.target.checked)}
              />
              I confirm these are the environments and times I expect to have available.
            </label>
            <button type="submit" disabled={!confirmed || windows.length === 0}>
              {state === "saving" ? "Saving availability…" : "Confirm next week’s availability"}
            </button>
            {message ? (
              <p className="form-error" role="alert">
                {message}
              </p>
            ) : null}
          </fieldset>
        </form>
      ) : null}

      {week.review.confirmed_availability &&
      (week.review.status === "environment_revision_required" ||
        week.review.status === "ready_to_finalize_next_week") ? (
        <section className="availability-form" aria-label="Confirmed next-week availability">
          <p className="eyebrow">Confirmed availability</p>
          <ul className="review-outcomes">
            {week.review.confirmed_availability.windows.map((window) => (
              <li key={`${window.environment_id}-${window.starts_at}`}>
                <strong>{window.environment_name}</strong>{" "}
                {new Date(window.starts_at).toLocaleString()}–
                {new Date(window.ends_at).toLocaleTimeString()}
              </li>
            ))}
          </ul>
          {week.review.status === "environment_revision_required" ? (
            <p className="form-help">
              {week.review.unresolved_environment_prescriptions} prescription(s) need reviewed
              exercise and dose decisions. Your confirmed times are saved; the PWA will not invent
              substitutions.
            </p>
          ) : (
            <button type="button" disabled={state === "saving"} onClick={finalizeNextWeek}>
              {state === "saving" ? "Finalizing next week…" : "Finalize next week"}
            </button>
          )}
          {message ? (
            <p className="form-error" role="alert">
              {message}
            </p>
          ) : null}
        </section>
      ) : null}

      {week.review.status === "next_week_already_prepared" && week.review.next_week_start ? (
        <button
          className="review-navigation"
          type="button"
          onClick={() => void onWeekPrepared(week.review.next_week_start!)}
        >
          Open next week →
        </button>
      ) : null}
    </section>
  );
}
