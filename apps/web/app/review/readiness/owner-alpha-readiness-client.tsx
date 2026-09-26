"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { localIsoDate } from "@/lib/current-week";
import {
  fetchOwnerAlphaReadinessAudit,
  type AthleteLiveAudit,
  type AuthorityGroupAudit,
  type OwnerAlphaReadinessAudit,
} from "@/lib/owner-alpha-readiness";
import { planningReviewHref } from "@/lib/planning-review-queue";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const initialAuditDate = localIsoDate();

function label(value: string): string {
  return value.replaceAll("_", " ");
}

function AuthorityGroup({ group }: { group: AuthorityGroupAudit }) {
  const ratified = group.items.filter((item) => item.status === "ratified").length;
  return (
    <article className="readiness-authority-group">
      <header>
        <div>
          <p className="eyebrow">{group.projection_version}</p>
          <h2>{group.label}</h2>
        </div>
        <span className="status-badge">{ratified} / {group.items.length} ratified</span>
      </header>
      <div className="readiness-candidates">
        {group.items.map((item) => (
          <section key={item.candidate_id}>
            <header>
              <strong>{item.release_label}</strong>
              <span className={`status-badge status-badge--${item.status}`}>
                {item.status}
              </span>
            </header>
            <dl>
              <div><dt>Candidate</dt><dd><code>{item.candidate_id}</code></dd></div>
              <div><dt>Ratified</dt><dd>{item.ratified_at ? new Date(item.ratified_at).toLocaleString() : "No"}</dd></div>
            </dl>
            <details>
              <summary>Exact digest and issues</summary>
              <code>{item.content_digest}</code>
              {item.issues.length ? <ul>{item.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul> : <p>No candidate conflict or prerequisite issue reported.</p>}
            </details>
          </section>
        ))}
      </div>
    </article>
  );
}

function AthleteState({ athlete }: { athlete: AthleteLiveAudit }) {
  const week = athlete.current_week?.week;
  return (
    <article className="readiness-athlete">
      <header>
        <div>
          <p className="eyebrow">Owned athlete</p>
          <h2>{athlete.athlete_display_name}</h2>
        </div>
        <span className={`status-badge status-badge--${athlete.current_week_error ? "conflict" : week ? "ratified" : "available"}`}>
          {athlete.current_week_error ? "inspection failed" : week ? "week persisted" : "no current week"}
        </span>
      </header>
      <code>{athlete.athlete_id}</code>
      {athlete.current_week_error ? (
        <p className="form-error">{athlete.current_week_error}</p>
      ) : week ? (
        <dl className="review-metadata">
          <div><dt>Weekly plan</dt><dd><code>{week.weekly_plan_id}</code></dd></div>
          <div><dt>Block week</dt><dd>{week.block_week}</dd></div>
          <div><dt>Dates</dt><dd>{week.week_start} – {week.week_end}</dd></div>
          <div><dt>Sessions</dt><dd>{week.sessions.length}</dd></div>
          <div><dt>Review state</dt><dd>{label(week.review.status)}</dd></div>
          <div><dt>Safety authority</dt><dd>{athlete.current_week?.safety_policy_assignment ? "assigned" : "missing"}</dd></div>
        </dl>
      ) : (
        <p className="planning-queue-empty">The authenticated current-week projection returned no persisted week for this date.</p>
      )}
      {athlete.planning_task ? (
        <section className="readiness-next-boundary">
          <strong>Next reviewer boundary</strong>
          <span>{label(athlete.planning_task.workflow_stage)} · {athlete.planning_task.readiness}</span>
          <p>{athlete.planning_task.message}</p>
          <Link className="text-link" href={planningReviewHref(athlete.planning_task)}>
            Inspect exact boundary →
          </Link>
        </section>
      ) : (
        <p className="form-help">No current planning-queue item was returned for this athlete.</p>
      )}
    </article>
  );
}

export function OwnerAlphaReadinessClient() {
  const [on, setOn] = useState(initialAuditDate);
  const [audit, setAudit] = useState<OwnerAlphaReadinessAudit | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const refresh = useCallback(async (auditDate: string) => {
    setLoading(true);
    setMessage("");
    try {
      setAudit(await fetchOwnerAlphaReadinessAudit(apiBaseUrl, auditDate));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to inspect owner-alpha readiness.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    void fetchOwnerAlphaReadinessAudit(apiBaseUrl, initialAuditDate)
      .then((result) => {
        if (active) setAudit(result);
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(error instanceof Error ? error.message : "Unable to inspect owner-alpha readiness.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const counts = useMemo(() => {
    const items = audit?.authority_groups.flatMap((group) => group.items) ?? [];
    return {
      ratified: items.filter((item) => item.status === "ratified").length,
      unresolved: items.filter((item) => item.status === "available" || item.status === "blocked").length,
      conflicts: items.filter((item) => item.status === "conflict").length,
      persistedWeeks: audit?.athletes.filter((athlete) => athlete.current_week?.week).length ?? 0,
    };
  }, [audit]);

  return (
    <main className="review-shell readiness-audit">
      <header className="review-topbar">
        <div>
          <p className="eyebrow">AGAS · Live operational evidence</p>
          <h1>Owner-alpha readiness audit</h1>
          <p>Inspect immutable candidate status and athlete-owned current-week state from the connected database.</p>
        </div>
        <nav className="review-route-links" aria-label="Reviewer routes">
          <Link href="/review/queue" className="text-link">Reviewer queue</Link>
          <Link href="/review/planning-authorities" className="text-link">Planning authorities</Link>
          <Link href="/review/assessments" className="text-link">Assessment governance</Link>
          <Link href="/" className="text-link">Athlete PWA</Link>
        </nav>
      </header>

      <aside className="review-boundary">
        <strong>This is an inspection, not an approval.</strong>
        <span>Candidate statuses come from digest-bound decision records. The inventory does not declare every candidate necessary for every athlete; each prepared planning step still resolves its exact dependencies and fails closed.</span>
      </aside>

      <section className="planning-queue-summary" aria-labelledby="readiness-summary-title">
        <header>
          <div>
            <p className="eyebrow">Point-in-time database projection</p>
            <h2 id="readiness-summary-title">Live state</h2>
          </div>
          <div className="readiness-date-control">
            <label htmlFor="readiness-on">Audit date</label>
            <input
              id="readiness-on"
              type="date"
              value={on}
              onChange={(event) => {
                const value = event.target.value;
                setOn(value);
                void refresh(value);
              }}
            />
            <button type="button" className="secondary-button" disabled={loading} onClick={() => void refresh(on)}>
              {loading ? "Inspecting…" : "Refresh live state"}
            </button>
          </div>
        </header>
        <dl className="review-metadata readiness-counts">
          <div><dt>Ratified candidates</dt><dd>{counts.ratified}</dd></div>
          <div><dt>Available or blocked</dt><dd>{counts.unresolved}</dd></div>
          <div><dt>Conflicts</dt><dd>{counts.conflicts}</dd></div>
          <div><dt>Owned athletes</dt><dd>{audit?.athletes.length ?? 0}</dd></div>
          <div><dt>Persisted current weeks</dt><dd>{counts.persistedWeeks}</dd></div>
        </dl>
      </section>

      {message ? <p className="form-error review-message" role="alert">{message}</p> : null}
      {!audit && loading ? <p className="planning-queue-empty">Loading authenticated database state…</p> : null}
      {audit ? (
        <>
          <section className="readiness-athletes" aria-label="Owned athlete live state">
            {audit.athletes.length ? audit.athletes.map((athlete) => <AthleteState key={athlete.athlete_id} athlete={athlete} />) : <p className="planning-queue-empty">The signed-in account owns no athlete profile.</p>}
          </section>
          <section className="readiness-authorities" aria-label="Authority candidate inventory">
            {audit.authority_groups.map((group) => <AuthorityGroup key={group.key} group={group} />)}
          </section>
          <p className="form-help">Audited for {audit.audited_on} · directory {audit.directory_projection_version} · queue {audit.queue_projection_version} projected {new Date(audit.queue_projected_at).toLocaleString()}</p>
        </>
      ) : null}
    </main>
  );
}
