"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  fetchAthleteDemographics,
  submitDateOfBirthReport,
  type AthleteDemographicsProjection,
} from "@/lib/athlete-demographics";

function localIsoDate(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

export function AthleteDemographicsPanel({
  apiBaseUrl,
  athleteId,
  onSaved,
}: {
  apiBaseUrl: string;
  athleteId: string;
  onSaved: () => void;
}) {
  const [projection, setProjection] = useState<AthleteDemographicsProjection | null>(null);
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [state, setState] = useState<"loading" | "ready" | "saving" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    void fetchAthleteDemographics(apiBaseUrl, athleteId)
      .then((result) => {
        if (active) {
          setProjection(result);
          setDateOfBirth(result.date_of_birth ?? "");
          setMessage("");
          setState("ready");
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(error instanceof Error ? error.message : "Unable to load age information.");
          setState("error");
        }
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl, athleteId]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("saving");
    setMessage("");
    try {
      const result = await submitDateOfBirthReport(apiBaseUrl, athleteId, dateOfBirth);
      setProjection(result.demographics);
      setDateOfBirth(result.demographics.date_of_birth ?? "");
      setMessage(
        result.created
          ? "Date of birth saved as a new historical report."
          : "This exact report was already saved.",
      );
      setState("ready");
      onSaved();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save date of birth.");
      setState("error");
    }
  }

  return (
    <section className="demographics-panel" aria-labelledby="demographics-title">
      <header className="demographics-panel__heading">
        <div>
          <p className="eyebrow">Planning applicability</p>
          <h2 id="demographics-title">Your age keeps evidence in the right lane.</h2>
        </div>
        {projection?.age_years !== null && projection ? (
          <span className="status-badge status-badge--ready">Age {projection.age_years}</span>
        ) : (
          <span className="status-badge status-badge--available">Age needed</span>
        )}
      </header>

      <p className="assessment-message">
        AGAS uses date of birth only to check whether age-specific assessment and planning rules
        apply. It does not treat age as a capability score.
      </p>
      {projection ? <p className="form-help">{projection.message}</p> : null}

      <form className="demographics-form" onSubmit={submit}>
        <label htmlFor="athlete-date-of-birth">
          Date of birth
          <input
            id="athlete-date-of-birth"
            type="date"
            value={dateOfBirth}
            max={localIsoDate()}
            onChange={(event) => setDateOfBirth(event.target.value)}
            required
          />
        </label>
        <label className="demographics-confirmation">
          <input type="checkbox" required />
          <span>I confirm this date is correct.</span>
        </label>
        <button type="submit" disabled={state === "saving" || !dateOfBirth}>
          {state === "saving"
            ? "Saving…"
            : projection?.source_kind === "reported_observation"
              ? "Save correction"
              : "Save date of birth"}
        </button>
      </form>

      {state === "loading" ? <p className="form-help">Loading age information…</p> : null}
      {message ? (
        <p className={state === "error" ? "form-error" : "form-success"} role="status">
          {message}
        </p>
      ) : null}
      {projection?.report_count ? (
        <p className="form-help">
          {projection.report_count} report(s) retained · projection {projection.projection_version}
        </p>
      ) : null}
    </section>
  );
}
