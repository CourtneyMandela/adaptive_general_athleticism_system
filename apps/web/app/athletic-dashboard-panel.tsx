"use client";

import { useCallback, useEffect, useState } from "react";

import {
  capabilityDomainLabel,
  capabilityValueLabel,
  fetchAthleticDashboard,
  type AthleticDashboardProjection,
} from "@/lib/athletic-dashboard";

function label(value: string): string {
  return value.replaceAll("_", " ");
}

export function AthleticDashboardPanel({
  apiBaseUrl,
  athleteId,
}: {
  apiBaseUrl: string;
  athleteId: string;
}) {
  const [projection, setProjection] = useState<AthleticDashboardProjection | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setState("loading");
    setMessage("");
    try {
      setProjection(await fetchAthleticDashboard(apiBaseUrl, athleteId));
      setState("ready");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load capability history.");
      setState("error");
    }
  }, [apiBaseUrl, athleteId]);

  useEffect(() => {
    let active = true;
    void fetchAthleticDashboard(apiBaseUrl, athleteId)
      .then((result) => {
        if (active) {
          setProjection(result);
          setMessage("");
          setState("ready");
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(error instanceof Error ? error.message : "Unable to load capability history.");
          setState("error");
        }
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl, athleteId]);

  const estimated = projection?.domains.filter((item) => item.status !== "not_estimated") ?? [];
  const unestimated = projection?.domains.filter((item) => item.status === "not_estimated") ?? [];

  return (
    <section className="athletic-dashboard" aria-labelledby="athletic-dashboard-title">
      <header className="athletic-dashboard__heading">
        <div>
          <p className="eyebrow">Athletic dashboard</p>
          <h2 id="athletic-dashboard-title">What is measured—and how certain it is.</h2>
        </div>
        <button type="button" className="text-button" onClick={() => void load()} disabled={state === "loading"}>
          {state === "loading" ? "Loading…" : "Refresh"}
        </button>
      </header>

      <p className="assessment-message">
        Values below are derived estimates, not ground truth or comparable 0–100 scores. Different
        scopes stay separate until a reviewed conversion says otherwise.
      </p>
      {message ? <p className="form-error" role="alert">{message}</p> : null}
      {projection ? (
        <>
          <dl className="dashboard-coverage">
            <div>
              <dt>Domains with an estimate</dt>
              <dd>{projection.estimated_domain_count}</dd>
            </div>
            <div>
              <dt>Not yet estimated</dt>
              <dd>{projection.unestimated_domain_count}</dd>
            </div>
          </dl>
          {estimated.length ? (
            <div className="capability-domain-grid">
              {estimated.map((domain) => (
                <article className="capability-domain-card" key={domain.domain}>
                  <header>
                    <h3>{capabilityDomainLabel(domain.domain)}</h3>
                    <span className={`status-badge status-badge--${domain.status}`}>
                      {label(domain.status)}
                    </span>
                  </header>
                  <p className="form-help">
                    {domain.historical_estimate_count} historical estimate(s) retained
                  </p>
                  <div className="capability-series-list">
                    {domain.latest_estimates.map((series) => (
                      <section key={`${series.estimate_scope}:${series.unit_or_scale}`}>
                        <div className="capability-value-line">
                          <strong>{capabilityValueLabel(series.estimate, series.unit_or_scale)}</strong>
                          <span>{series.confidence} confidence · {series.status}</span>
                        </div>
                        <p>{series.estimate_scope}</p>
                        <details>
                          <summary>Method and provenance</summary>
                          <p>
                            Derived by {series.calculation_method} · rule {series.rule_version}
                          </p>
                          <p>
                            Estimated {new Date(series.estimated_at).toLocaleString()}
                            {series.valid_until
                              ? ` · valid until ${new Date(series.valid_until).toLocaleString()}`
                              : " · no explicit validity end"}
                          </p>
                          <p>
                            {series.source_observation_ids.length} source observation(s) · {" "}
                            {series.historical_estimate_count} estimate(s) in this exact series
                          </p>
                        </details>
                      </section>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="dashboard-empty">
              No capability estimate has been derived yet. Assessment observations remain separate
              until a reviewed interpretation policy creates one.
            </p>
          )}
          {unestimated.length ? (
            <details className="unestimated-domains">
              <summary>{unestimated.length} domains without a current measurement series</summary>
              <ul>
                {unestimated.map((domain) => (
                  <li key={domain.domain}>{capabilityDomainLabel(domain.domain)}</li>
                ))}
              </ul>
            </details>
          ) : null}
          <p className="form-help">Projection {projection.projection_version}</p>
        </>
      ) : state === "loading" ? (
        <p className="form-help">Loading provenance-bearing capability history…</p>
      ) : null}
    </section>
  );
}
