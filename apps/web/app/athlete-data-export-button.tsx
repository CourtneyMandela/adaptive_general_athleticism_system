"use client";

import { useState } from "react";

import {
  athleteDataExportFilename,
  fetchAthleteDataExport,
} from "@/lib/athlete-data-export";

export function AthleteDataExportButton({
  apiBaseUrl,
  athleteId,
}: {
  apiBaseUrl: string;
  athleteId: string;
}) {
  const [state, setState] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  async function download() {
    setState("loading");
    setMessage("");
    try {
      const payload = await fetchAthleteDataExport(apiBaseUrl, athleteId);
      const blob = new Blob([`${JSON.stringify(payload, null, 2)}\n`], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = athleteDataExportFilename(payload);
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
      setState("success");
      setMessage(
        `Downloaded ${payload.manifest.record_count} records. Keep this private; recovery remains an operator-controlled procedure.`,
      );
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Unable to download your data.");
    }
  }

  return (
    <div className="athlete-export">
      <button
        type="button"
        className="text-button"
        disabled={state === "loading"}
        onClick={() => void download()}
      >
        {state === "loading" ? "Preparing data…" : "Download my data"}
      </button>
      <p className={state === "error" ? "form-error" : "form-help"} aria-live="polite">
        {message}
      </p>
    </div>
  );
}
