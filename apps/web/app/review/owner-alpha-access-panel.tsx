"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  activateOwnerAlphaAccess,
  fetchOwnerAlphaAccess,
  type OwnerAlphaAccessProjection,
} from "@/lib/owner-alpha-access";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function readableRole(value: string): string {
  return value.replaceAll("_", " ");
}

export function OwnerAlphaAccessPanel() {
  const [projection, setProjection] = useState<OwnerAlphaAccessProjection | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    fetchOwnerAlphaAccess(apiBaseUrl)
      .then((result) => {
        if (active) setProjection(result);
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(error instanceof Error ? error.message : "Unable to check reviewer access.");
        }
      })
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function activate() {
    if (!confirmed) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await activateOwnerAlphaAccess(apiBaseUrl);
      setProjection(result.access);
      setConfirmed(false);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to activate reviewer access.");
    } finally {
      setBusy(false);
    }
  }

  if (busy && !projection) {
    return <aside className="owner-access owner-access--loading">Checking reviewer access…</aside>;
  }
  if (!projection) {
    return (
      <aside className="owner-access owner-access--blocked" role="status">
        <strong>Reviewer access could not be checked.</strong>
        <span>{message || "Sign in and retry."}</span>
      </aside>
    );
  }
  if (projection.status === "active") {
    return (
      <aside className="owner-access owner-access--active" role="status">
        <strong>Owner-alpha review access active</strong>
        <span>Assessment and planning approvals are available to this signed-in account.</span>
      </aside>
    );
  }

  return (
    <aside className="owner-access owner-access--blocked" aria-labelledby="owner-access-title">
      <div>
        <p className="eyebrow">One-time owner setup</p>
        <h2 id="owner-access-title">Reviewer access is not active yet.</h2>
        <p>{projection.message}</p>
      </div>
      <dl>
        <div>
          <dt>Signed-in subject</dt>
          <dd><code>{projection.authenticated_subject}</code></dd>
        </div>
        {projection.roles.map((role) => (
          <div key={role.role}>
            <dt>{readableRole(role.role)}</dt>
            <dd>{role.status ?? "not granted"}</dd>
          </div>
        ))}
      </dl>
      {projection.status === "not_configured" ? (
        <p className="owner-access__instruction">
          Set the Render secret <code>AGAS_OWNER_ALPHA_OPERATOR_SUBJECT</code> to the exact signed-in
          subject above, redeploy the API, then return here. Never use <code>*</code>.
        </p>
      ) : null}
      {projection.status === "account_required" || projection.status === "athlete_required" ? (
        <Link className="secondary-button" href="/">Finish athlete setup</Link>
      ) : null}
      {projection.can_activate ? (
        <div className="owner-access__activation">
          <label>
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(event) => setConfirmed(event.target.checked)}
            />
            <span>
              I understand these are application permissions to review AGAS-prepared artifacts;
              they do not claim a scientific or professional credential.
            </span>
          </label>
          <button
            type="button"
            className="primary-button"
            disabled={!confirmed || busy}
            onClick={() => void activate()}
          >
            {busy ? "Activating…" : "Activate owner review access"}
          </button>
        </div>
      ) : null}
      {message ? <p className="form-error" role="alert">{message}</p> : null}
    </aside>
  );
}
