import { expect, test, type APIResponse } from "@playwright/test";

import { OIDC_TRANSACTION_COOKIE_NAME } from "../lib/oidc-login";
import { SESSION_COOKIE_NAME } from "../lib/server-session";

const athleteId = "d0000000-0000-4000-8000-000000000001";

test("reviewer workbench exposes the synthetic athlete's honest next boundary", async ({
  page,
}) => {
  await page.route("http://localhost:8000/v1/operator/planning-review-queue**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projected_at: "2026-08-30T14:00:00Z",
        projection_version: "planning-review-queue@1.0.0",
        items: [
          {
            workflow_stage: "initial_planning",
            status: "capability_estimate_required",
            readiness: "blocked",
            athlete_id: athleteId,
            athlete_display_name: "Synthetic four-day traveler",
            strategy_id: null,
            block_id: null,
            message: "No current capability estimate is available for initial planning.",
            issues: ["No current capability estimate is available for initial planning."],
          },
        ],
      }),
    }),
  );

  await page.goto("/review/queue");

  await expect(page.getByRole("heading", { name: "Reviewer workbench" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Synthetic four-day traveler" })).toBeVisible();
  await expect(page.getByText("capability estimate required")).toBeVisible();
  await expect(page.getByRole("link", { name: "Inspect blockers" })).toHaveAttribute(
    "href",
    `/review?athleteId=${athleteId}`,
  );
});

test("the bootstrap athlete deep link opens the PWA without UUID copy and paste", async ({
  page,
}) => {
  await page.route("http://localhost:8000/v1/**", (route) => {
    if (route.request().url().includes(`/athletes/${athleteId}/current-week`)) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-08-30",
          safety_policy_assignment: null,
          week: null,
        }),
      });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not needed by this navigation smoke test" }),
    });
  });

  await page.goto(`/?athleteId=${athleteId}`);

  await expect(page.getByRole("heading", { name: "Synthetic four-day traveler" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Change athlete" })).toBeVisible();
  await expect(page.getByText("There is no persisted plan covering")).toBeVisible();
});

test("assessment workbench makes missing scientific governance explicit", async ({ page }) => {
  await page.route("http://localhost:8000/v1/operator/assessment-governance**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projected_at: "2026-08-30T16:00:00Z",
        projection_version: "assessment-governance-workbench@1.1.0",
        items: [
          {
            definition: {
              id: "a0000000-0000-4000-8000-000000000001",
              slug: "fixture_cycle",
              name: "Fixture cycle",
              domain: "aerobic_capacity",
              observation_type: "fixture_cycle_result",
              intensity: "moderate",
              unit_or_scale: "w",
              protocol_version: "fixture-cycle@1.0.0",
            },
            status: "unreviewed",
            readiness: "blocked",
            current_review: null,
            review_history: [],
            current_estimation_policy: null,
            estimation_policy_history: [],
            evidence_claims: [],
            review_evidence_governance: null,
            estimation_policy_evidence_governance: null,
            issues: [
              "assessment definition has no protocol review history",
              "no capability-estimation policy exists for this definition",
            ],
          },
        ],
      }),
    }),
  );

  await page.goto("/review/assessments");

  await expect(page.getByRole("heading", { name: "Assessment governance" })).toBeVisible();
  await expect(page.getByText("Access is not scientific qualification.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Fixture cycle" })).toBeVisible();
  await expect(page.getByText("assessment definition has no protocol review history")).toBeVisible();
  await expect(page.getByText("No capability-estimation policy exists.")).toBeVisible();
});

test("the installable shell fails closed to an honest offline screen", async ({ context, page }) => {
  await page.goto("/");

  const manifestResponse = await page.request.get("/manifest.webmanifest");
  expect(manifestResponse.ok()).toBe(true);
  const manifest = (await manifestResponse.json()) as {
    display?: string;
    icons?: { purpose?: string; src?: string }[];
  };
  expect(manifest.display).toBe("standalone");
  expect(manifest.icons).toEqual(
    expect.arrayContaining([
      expect.objectContaining({ purpose: "any", src: "/icons/agas-icon.svg" }),
      expect.objectContaining({ purpose: "maskable", src: "/icons/agas-icon-maskable.svg" }),
    ]),
  );

  await page.evaluate(async () => {
    await navigator.serviceWorker.register("/sw.js", { scope: "/" });
    await navigator.serviceWorker.ready;
    if (navigator.serviceWorker.controller) return;
    await new Promise<void>((resolve) => {
      navigator.serviceWorker.addEventListener("controllerchange", () => resolve(), { once: true });
    });
  });

  await context.setOffline(true);
  try {
    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "You’re offline" })).toBeVisible();
    await expect(page.getByText("No athlete data is shown, changed, or queued")).toBeVisible();
  } finally {
    await context.setOffline(false);
  }
});

test("the same-origin API gateway fails closed without a server session", async ({ request }) => {
  const response = await request.get("/api/agas/v1/athletes/athlete-1/current-week");

  expect(response.status()).toBe(401);
  expect(response.headers()["cache-control"]).toBe("no-store");
  expect(await response.json()).toEqual({ detail: "Authentication is required." });
});

function responseCookie(response: APIResponse, name: string): string {
  const header = response
    .headersArray()
    .find(({ name: headerName, value }) =>
      headerName.toLowerCase() === "set-cookie" && value.startsWith(`${name}=`),
    )?.value;
  const match = new RegExp(`^${name}=([^;,]+)`).exec(header ?? "");
  expect(match, `${name} must be set`).not.toBeNull();
  return `${name}=${match?.[1] ?? ""}`;
}

test("browser login establishes an encrypted session that reaches the private API", async ({
  request,
}) => {
  const login = await request.get("/auth/login?return_to=%2F", { maxRedirects: 0 });
  expect(login.status()).toBe(303);
  expect(login.headers()["cache-control"]).toBe("no-store");
  const transactionCookie = responseCookie(login, OIDC_TRANSACTION_COOKIE_NAME);
  const authorizationUrl = login.headers().location;
  expect(authorizationUrl).toContain("http://127.0.0.1:3998/authorize?");
  expect(authorizationUrl).toContain("code_challenge_method=S256");

  const authorization = await request.get(authorizationUrl, { maxRedirects: 0 });
  expect(authorization.status()).toBe(303);
  const callbackUrl = authorization.headers().location;
  expect(callbackUrl).toContain("http://127.0.0.1:3100/auth/callback?");

  const callback = await request.get(callbackUrl, {
    headers: { cookie: transactionCookie },
    maxRedirects: 0,
  });
  expect(callback.status()).toBe(303);
  expect(callback.headers().location).toBe("http://127.0.0.1:3100/");
  const sessionCookie = responseCookie(callback, SESSION_COOKIE_NAME);
  expect(sessionCookie).not.toContain("agas-e2e-access-token");

  const privateResponse = await request.get("/api/agas/v1/conformance/session", {
    headers: { cookie: sessionCookie },
  });
  expect(privateResponse.status()).toBe(200);
  expect(privateResponse.headers()["cache-control"]).toBe("no-store");
  expect(await privateResponse.json()).toEqual({
    authorization_received: true,
    subject: "e2e-athlete-owner",
  });

  const replay = await request.get(callbackUrl, {
    headers: { cookie: transactionCookie },
    maxRedirects: 0,
  });
  expect(replay.status()).toBe(502);
  expect(await replay.json()).toEqual({
    detail: "Identity provider returned an invalid response.",
  });
});
