"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  fetchPlanningReviewQueue,
  planningReviewHref,
  type PlanningReviewQueueProjection,
  type PlanningWorkflowStage,
} from "@/lib/planning-review-queue";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const stageLabels: Record<PlanningWorkflowStage, string> = {
  initial_planning: "Initial planning",
  resource_demands: "Resource demands",
  block_creation: "Block creation",
  first_week: "Week 1 authoring",
};

function label(value: string): string {
  return value.replaceAll("_", " ");
}

export function PlanningReviewQueueClient() {
  const [projection, setProjection] = useState<PlanningReviewQueueProjection | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      setProjection(await fetchPlanningReviewQueue(apiBaseUrl));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load reviewer work.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    fetchPlanningReviewQueue(apiBaseUrl)
      .then((result) => {
        if (active) setProjection(result);
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(error instanceof Error ? error.message : "Unable to load reviewer work.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const readyCount = projection?.items.filter((item) => item.readiness === "ready").length ?? 0;
  const blockedCount = projection?.items.filter((item) => item.readiness === "blocked").length ?? 0;

  return (
    <main className="review-shell">
      <header className="review-topbar">
        <div>
          <p className="eyebrow">AGAS · Planning authority</p>
          <h1>Reviewer workbench</h1>
          <p>Continue each athlete from the next explicit, provenance-preserving planning boundary.</p>
        </div>
        <nav className="review-route-links" aria-label="Reviewer routes">
          <Link href="/review/assessments" className="text-link">Assessment governance</Link>
          <Link href="/review/post-block" className="text-link">Post-block queue</Link>
          <Link href="/" className="text-link">Athlete PWA</Link>
        </nav>
      </header>

      <aside className="review-boundary">
        <strong>The queue does not make training decisions.</strong>
        <span>It derives the next missing workflow boundary from persisted history. Every destination reloads its complete authoritative preparation before a reviewer can write.</span>
      </aside>

      <section className="planning-queue-summary" aria-labelledby="planning-queue-title">
        <header>
          <div>
            <p className="eyebrow">Derived lifecycle queue</p>
            <h2 id="planning-queue-title">Planning work</h2>
          </div>
          <button type="button" className="secondary-button" disabled={loading} onClick={() => void refresh()}>
            {loading ? "Refreshing…" : "Refresh queue"}
          </button>
        </header>
        <dl className="review-metadata">
          <div><dt>Ready</dt><dd>{readyCount}</dd></div>
          <div><dt>Blocked</dt><dd>{blockedCount}</dd></div>
          <div><dt>Total athletes</dt><dd>{projection?.items.length ?? 0}</dd></div>
        </dl>
      </section>

      {message ? <p className="form-error review-message" role="alert">{message}</p> : null}
      {!projection && loading ? <p className="planning-queue-empty">Loading reviewer work…</p> : null}
      {projection && !projection.items.length ? (
        <p className="planning-queue-empty">No athlete currently requires reviewer-owned planning work.</p>
      ) : null}
      {projection?.items.length ? (
        <section className="planning-queue-items" aria-label="Planning queue items">
          {projection.items.map((item) => (
            <article key={item.athlete_id}>
              <header>
                <div>
                  <p className="eyebrow">{stageLabels[item.workflow_stage]}</p>
                  <h2>{item.athlete_display_name}</h2>
                </div>
                <span className={`status-badge status-badge--${item.readiness}`}>
                  {item.readiness}
                </span>
              </header>
              <p>{item.message}</p>
              <dl>
                <div><dt>Current boundary</dt><dd>{label(item.status)}</dd></div>
                <div><dt>Athlete</dt><dd><code>{item.athlete_id}</code></dd></div>
              </dl>
              {item.issues.length ? (
                <section className="planning-queue-blockers">
                  <strong>{item.issues.length} prerequisite issue(s)</strong>
                  <ul>{item.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul>
                </section>
              ) : null}
              <Link className={item.readiness === "ready" ? "primary-button" : "secondary-button"} href={planningReviewHref(item)}>
                {item.readiness === "ready" ? "Open review" : "Inspect blockers"}
              </Link>
            </article>
          ))}
        </section>
      ) : null}
      {projection ? (
        <p className="form-help">Projected {new Date(projection.projected_at).toLocaleString()} · {projection.projection_version}</p>
      ) : null}
    </main>
  );
}
