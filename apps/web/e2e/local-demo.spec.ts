import { expect, test } from "@playwright/test";

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
