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

test("the phone workflow turns a factual readiness report into a narrow decision", async ({
  page,
}) => {
  let readinessAllowed = false;
  let submittedBody: Record<string, unknown> | null = null;
  await page.route("http://localhost:8000/v1/**", async (route) => {
    const request = route.request();
    if (request.url().includes(`/athletes/${athleteId}/assessment-readiness-reports`)) {
      submittedBody = request.postDataJSON() as Record<string, unknown>;
      readinessAllowed = true;
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          observation_id: "d1000000-0000-4000-8000-000000000001",
          eligibility_review_id: "d1000000-0000-4000-8000-000000000002",
          outcome: "selection_allowed",
          maximum_assessment_intensity: "moderate",
          valid_until: "2026-09-09T16:00:00Z",
          next_action: "Continue to governed low/moderate assessment selection.",
          created: true,
          rule_version: "assessment-readiness-screen@1.0.0",
        }),
      });
    }
    if (request.url().includes(`/athletes/${athleteId}/assessment-workflow`)) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-09-08T16:00:00Z",
          status: readinessAllowed ? "environment_required" : "eligibility_required",
          message: readinessAllowed
            ? "At least one persisted environment is required for assessment selection."
            : "A current readiness decision is required before assessment selection.",
          can_start_run: false,
          can_record_results: false,
          approved_self_administered_protocol_count: 1,
          due_protocol_count: 1,
          next_reassessment_at: null,
          reassessment_rule_version: "assessment-reassessment-schedule@1.0.0",
          eligibility: readinessAllowed
            ? {
                eligibility_review_id: "d1000000-0000-4000-8000-000000000002",
                outcome: "selection_allowed",
                reviewed_at: "2026-09-08T16:00:00Z",
                valid_until: "2026-09-09T16:00:00Z",
                maximum_assessment_intensity: "moderate",
                rule_version: "assessment-readiness-screen@1.0.0",
              }
            : null,
          environments: [],
          latest_run: null,
        }),
      });
    }
    if (request.url().includes(`/athletes/${athleteId}/current-week`)) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-09-08",
          safety_policy_assignment: null,
          week: null,
        }),
      });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not needed by readiness browser test" }),
    });
  });

  await page.goto(`/?athleteId=${athleteId}`);
  await expect(page.getByText("This is a stop/go screen, not medical clearance.")).toBeVisible();
  const submit = page.getByRole("button", { name: "Evaluate current readiness" });
  await expect(submit).toBeDisabled();
  await page.getByLabel("I confirm that I am an adult").check();
  await page.getByLabel("Has a healthcare professional told you that you have cardiovascular").selectOption("no");
  await page.getByLabel("Do you currently have any concerning signs or symptoms?").selectOption("no");
  await page.getByLabel("Has a healthcare professional told you to avoid or limit exercise").selectOption("no");
  await page.getByLabel("Do you currently have lower-body pain").selectOption("no");
  await page.getByLabel("Using the exact stable chair setup").selectOption("yes");
  await page.getByLabel("These answers describe my current state").check();
  await submit.click();

  await expect(page.getByText("Continue to governed low/moderate assessment selection.")).toBeVisible();
  expect(submittedBody).toMatchObject({
    adult_confirmed: true,
    concerning_signs_or_symptoms: "no",
    controlled_chair_stand_without_arms: "yes",
    answers_confirmed: true,
  });
  expect(submittedBody).not.toHaveProperty("outcome");
});

test("the phone workflow appends a date-of-birth report for age applicability", async ({
  page,
}) => {
  let submittedBody: Record<string, unknown> | null = null;
  await page.route("http://localhost:8000/v1/**", async (route) => {
    const request = route.request();
    if (request.url().includes(`/athletes/${athleteId}/date-of-birth-reports`)) {
      submittedBody = request.postDataJSON() as Record<string, unknown>;
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          observation_id: "d2000000-0000-4000-8000-000000000001",
          demographics: {
            athlete_id: athleteId,
            as_of: "2026-09-09T12:00:00Z",
            date_of_birth: "1990-01-03",
            age_years: 36,
            source_observation_id: "d2000000-0000-4000-8000-000000000001",
            source_kind: "reported_observation",
            report_count: 1,
            message: "Earlier reports remain in history.",
            projection_version: "athlete-demographics-projection@1.0.0",
          },
          created: true,
          rule_version: "athlete-date-of-birth-report@1.0.0",
        }),
      });
    }
    if (request.url().includes(`/athletes/${athleteId}/demographics`)) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          as_of: "2026-09-09T12:00:00Z",
          date_of_birth: null,
          age_years: null,
          source_observation_id: null,
          source_kind: "unknown",
          report_count: 0,
          message: "Date of birth has not been reported.",
          projection_version: "athlete-demographics-projection@1.0.0",
        }),
      });
    }
    if (request.url().includes(`/athletes/${athleteId}/current-week`)) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-09-09",
          safety_policy_assignment: null,
          week: null,
        }),
      });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not needed by demographics browser test" }),
    });
  });

  await page.goto(`/?athleteId=${athleteId}`);
  await expect(page.getByText("Age needed")).toBeVisible();
  await expect(page.getByText("Loading age information…")).toBeHidden();
  await page.getByLabel("Date of birth").fill("1990-01-03");
  await page.getByLabel("I confirm this date is correct.").check();
  await page.getByRole("button", { name: "Save date of birth" }).click();

  await expect(page.getByText("Date of birth saved as a new historical report.")).toBeVisible();
  await expect(page.getByText("Age 36")).toBeVisible();
  expect(submittedBody).toMatchObject({
    date_of_birth: "1990-01-03",
    date_of_birth_confirmed: true,
  });
  expect(submittedBody).not.toHaveProperty("age_years");
});

test("assessment workbench makes missing scientific governance explicit", async ({ page }) => {
  await page.route("http://localhost:8000/v1/operator/assessment-governance**", (route) => {
    if (route.request().url().endsWith("/candidates")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          projected_at: "2026-09-08T15:00:00Z",
          projection_version: "assessment-governance-candidates@1.0.0",
          items: [{
            status: "available",
            ratified_at: null,
            issues: [],
            candidate: {
              candidate_version: "assessment-governance-candidate@1.0.0",
              candidate_id: "94000000-0000-4000-8000-000000000001",
              slug: "thirty_second_chair_stand",
              release_label: "30-second chair stand owner-alpha release",
              prepared_at: "2026-09-08T10:45:00Z",
              content_digest: `sha256:${"a".repeat(64)}`,
              summary: "A narrow, repeatable first measurement.",
              measures: "Assessment-specific sit-to-stand performance.",
              does_not_measure: ["A universal athleticism score."],
              capability_domain: "muscular_endurance",
              estimate_scope: "assessment_specific:thirty_second_chair_stand_repetitions",
              setup_requirements: ["A stable armless chair."],
              protocol_steps: ["Complete controlled stands for 30 seconds."],
              stop_conditions: ["Stop for pain or dizziness."],
              operational_choices: ["A single result remains low confidence."],
              unresolved_limitations: ["Population transfer is uncertain."],
              evidence: [{
                title: "Primary validity study",
                source_url: "https://pubmed.ncbi.nlm.nih.gov/35949374/",
                population: "81 healthy adults aged 19-35.",
                finding: "Count correlated with comparator tests.",
                limitations: ["Single cross-sectional study."],
                conflict_disclosure: "No declared conflicts.",
              }],
            },
          }],
        }),
      });
    }
    return route.fulfill({
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
    });
  });

  await page.goto("/review/assessments");

  await expect(page.getByRole("heading", { name: "Assessment governance" })).toBeVisible();
  await expect(page.getByText("Access is not scientific qualification.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "30-second chair stand owner-alpha release" })).toBeVisible();
  await expect(page.getByText("A universal athleticism score.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve exact release" })).toBeDisabled();
  await expect(page.getByRole("heading", { name: "Fixture cycle" })).toBeVisible();
  await expect(page.getByText("assessment definition has no protocol review history")).toBeVisible();
  await expect(page.getByText("No capability-estimation policy exists.")).toBeVisible();
});

test("owner can ratify an exact prepared planning policy without authoring values", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  let ratified = false;
  let floorRatified = false;
  let submittedBody: Record<string, unknown> = {};
  let submittedFloorBody: Record<string, unknown> = {};
  const candidate = {
    candidate_version: "planning-governance-candidate@1.0.0",
    candidate_id: "98400000-0000-4000-8000-000000000001",
    slug: "owner_alpha_conservative_priority_policy",
    release_label: "Conservative owner-alpha priority policy",
    prepared_at: "2026-09-09T10:30:00Z",
    content_digest: `sha256:${"b".repeat(64)}`,
    summary: "A transparent first ranking policy.",
    governs: ["How reviewed inputs are combined."],
    does_not_establish: ["Which adaptation Courtney should develop."],
    operational_choices: ["At most two adaptations may receive DEVELOP status."],
    unresolved_limitations: ["The numerical policy is an engineering prior."],
    evidence: [{
      title: "ACSM resistance-training position stand (2026)",
      source_url: "https://pubmed.ncbi.nlm.nih.gov/41843416/",
      population: "Healthy adults.",
      finding: "Resistance training improved multiple outcomes.",
      limitations: ["The source does not validate ranking weights."],
      conflict_disclosure: "Full-text review remains pending.",
    }],
  };
  await page.route("http://localhost:8000/v1/operator/planning-governance/candidates**", async (route) => {
    if (route.request().method() === "POST") {
      submittedBody = route.request().postDataJSON() as Record<string, unknown>;
      ratified = true;
      return route.fulfill({ contentType: "application/json", body: JSON.stringify({ ok: true }) });
    }
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projected_at: "2026-09-09T15:00:00Z",
        projection_version: "planning-governance-candidates@1.0.0",
        items: [{
          candidate,
          status: ratified ? "ratified" : "available",
          ratified_at: ratified ? "2026-09-09T15:00:00Z" : null,
          issues: [],
        }],
      }),
    });
  });
  const floorCandidate = {
    candidate_version: "competency-floor-candidate@1.0.0",
    candidate_id: "98400000-0000-4000-8000-000000000002",
    slug: "chair_stand_age_30_39_lower_reference_floor",
    release_label: "Age 30-39 chair-stand lower-reference floor",
    prepared_at: "2026-09-09T00:10:00Z",
    content_digest: `sha256:${"c".repeat(64)}`,
    summary: "A deliberately low, provisional comparison point.",
    domain: "muscular_endurance",
    estimate_scope: "assessment_specific:thirty_second_chair_stand_repetitions",
    unit_or_scale: "repetitions",
    threshold: 11,
    comparison_direction: "higher_is_better",
    minimum_age_years: 30,
    maximum_age_years: 39,
    governs: ["Whether a matching estimate is below this provisional lower reference."],
    does_not_establish: ["Medical safety, diagnosis, or clearance to train."],
    unresolved_limitations: ["The source is Colombian and the subgroup is small."],
    evidence: [{
      title: "Colombian adult sit-to-stand reference values (2025)",
      source_url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC13193711/",
      population: "Colombian adults aged 30-39.",
      finding: "The p2.5 value was 11 repetitions in both sex strata.",
      limitations: ["A reference percentile is not a health or safety cutoff."],
      conflict_disclosure: "The authors reported no relevant financial involvement.",
    }],
  };
  await page.route("http://localhost:8000/v1/operator/competency-floor-candidates**", async (route) => {
    if (route.request().method() === "POST") {
      submittedFloorBody = route.request().postDataJSON() as Record<string, unknown>;
      floorRatified = true;
      return route.fulfill({ contentType: "application/json", body: JSON.stringify({ ok: true }) });
    }
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projected_at: "2026-09-10T15:00:00Z",
        projection_version: "competency-floor-candidates@1.0.0",
        items: [{
          candidate: floorCandidate,
          status: floorRatified ? "ratified" : "available",
          ratified_at: floorRatified ? "2026-09-10T15:00:00Z" : null,
          issues: [],
        }],
      }),
    });
  });

  await page.goto("/review/planning-authorities");

  await expect(page.getByRole("heading", { name: "Prepared planning authorities" })).toBeVisible();
  await expect(page.getByText("Which adaptation Courtney should develop.")).toBeVisible();
  const approve = page.getByRole("button", { name: "Approve exact policy" });
  await expect(approve).toBeDisabled();
  await page.getByLabel(/I reviewed the policy scope/).check();
  await approve.click();
  await expect(page.getByText(/This policy can now appear in initial-planning preparation/)).toBeVisible();
  expect(submittedBody).toEqual({
    candidate_version: candidate.candidate_version,
    content_digest: candidate.content_digest,
    approval_attestation: true,
  });
  expect(submittedBody).not.toHaveProperty("deficit_weight");

  await expect(page.getByRole("heading", { name: "Competency-floor candidates" })).toBeVisible();
  await expect(page.getByText("Medical safety, diagnosis, or clearance to train.")).toBeVisible();
  const approveFloor = page.getByRole("button", { name: "Approve exact floor" });
  await expect(approveFloor).toBeDisabled();
  await page.getByLabel(/I reviewed the population, exact threshold/).check();
  await approveFloor.click();
  await expect(page.getByText(/The floor can now be applied only/)).toBeVisible();
  expect(submittedFloorBody).toEqual({
    candidate_version: floorCandidate.candidate_version,
    content_digest: floorCandidate.content_digest,
    approval_attestation: true,
  });
  expect(submittedFloorBody).not.toHaveProperty("threshold");
});

test("owner can accept a system-prepared planning context without inventing scores", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const contextId = "98500000-0000-4000-8000-000000000001";
  const estimateId = "96000000-0000-4000-8000-000000000010";
  const floorId = "99000000-0000-4000-8000-000000000001";
  const floorReviewId = "99100000-0000-4000-8000-000000000001";
  const adaptationId = "a0000000-0000-4000-8000-000000000004";
  let submittedBody: Record<string, unknown> = {};
  const candidateContext = {
    adaptation_id: adaptationId,
    competency_floor_id: floorId,
    competency_floor_review_id: floorReviewId,
    capability_estimate_id: estimateId,
    general_relevance: 0,
    goal_relevance: 0,
    prerequisite_value: 0,
    expected_trainability: 0,
    transfer_value: 0,
    fatigue_cost: 0,
    time_cost: 0,
    interference_cost: 0,
    safe_to_train: true,
    introductory_exposure_needed: false,
    prerequisites_met: true,
    prerequisite_adaptation_ids: [],
    cultivate_comparative_advantage: false,
    source_observation_ids: ["93000000-0000-4000-8000-000000000010"],
    evidence_claim_ids: ["91000000-0000-4000-8000-000000000010"],
  };
  const draft = {
    id: contextId,
    schema_version: "1.0.0",
    created_at: "2026-09-10T16:00:00Z",
    athlete_id: athleteId,
    priority_policy_id: "98000000-0000-4000-8000-000000000002",
    priority_policy_review_id: "98300000-0000-4000-8000-000000000002",
    candidate_contexts: [candidateContext],
    horizon_months: 12,
    review_after_days: 28,
    authored_by_account_id: "10000000-0000-4000-8000-000000000001",
    author_authority_assignment_id: "20000000-0000-4000-8000-000000000001",
    authored_at: "2026-09-10T16:00:00Z",
    applicability_rationale: "System prepared exact context.",
    uncertainty: "No workout or medical clearance.",
    draft_version: "initial-planning-context-draft@1.0.0",
  };
  const candidate = {
    candidate_version: "prepared-initial-planning-context@1.0.0",
    candidate_id: contextId,
    content_digest: `sha256:${"d".repeat(64)}`,
    prepared_at: "2026-09-10T16:00:00Z",
    athlete_id: athleteId,
    athlete_display_name: "Courtney",
    status: "available",
    summary: "AGAS prepared the exact first planning context from governed state.",
    priority_policy_id: draft.priority_policy_id,
    priority_policy_review_id: draft.priority_policy_review_id,
    policy_version: "owner-alpha-deficit-only-priority@1.0.0",
    floor_version: "chair-stand-age-30-39-lower-reference-floor@1.0.0",
    estimate_scope: "assessment_specific:thirty_second_chair_stand_repetitions",
    candidate_context: candidateContext,
    horizon_months: 12,
    review_after_days: 28,
    applicability_rationale: "Zero means unused, not unimportant.",
    uncertainty: "The estimate is low confidence.",
    components: [{
      field: "general_relevance",
      value: 0,
      treatment: "unused",
      basis: "Explicit zero paired with zero policy weight.",
      limitation: "No governed magnitude exists.",
    }],
    expected_priority_state: "develop",
    expected_priority_score: 0.045,
    safety_boundary: "This is not medical clearance; each session needs its safety gate.",
    accepted_draft_id: null,
    accepted_draft: null,
    accepted_review: null,
  };
  await page.route(
    `http://localhost:8000/v1/operator/athletes/${athleteId}/initial-planning-preparation**`,
    (route) => route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        athlete_id: athleteId,
        athlete_display_name: "Courtney",
        projected_at: "2026-09-10T16:00:00Z",
        athlete_age_years: 35,
        status: "planning_context_review_required",
        message: "Ready for exact context review.",
        initial_strategy_id: null,
        estimate_options: [],
        stale_estimates: [],
        priority_policy_options: [],
        evidence_claims: [],
        floor_applicability_issues: [],
        projection_version: "initial-planning-preparation@1.1.0",
      }),
    }),
  );
  await page.route(
    `http://localhost:8000/v1/operator/athletes/${athleteId}/prepared-initial-planning-context**`,
    async (route) => {
      if (route.request().method() === "POST") {
        submittedBody = route.request().postDataJSON() as Record<string, unknown>;
        return route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            candidate_id: contextId,
            candidate_content_digest: candidate.content_digest,
            created: true,
            draft,
            ratification_version: "prepared-initial-planning-context-ratification@1.0.0",
          }),
        });
      }
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          projected_at: "2026-09-10T16:00:00Z",
          status: "available",
          message: "One exact context is ready.",
          candidate,
          blockers: [],
          projection_version: "prepared-initial-planning-context-projection@1.0.0",
        }),
      });
    },
  );

  await page.goto(`/review?athleteId=${athleteId}`);
  await page.getByRole("button", { name: "Load eligible inputs" }).click();
  await expect(page.getByRole("heading", { name: "Review what AGAS prepared" })).toBeVisible();
  await expect(page.getByText("DEVELOP", { exact: true })).toBeVisible();
  await expect(page.getByText("This is not medical clearance", { exact: false })).toBeVisible();
  const accept = page.getByRole("button", { name: "Accept prepared context" });
  await expect(accept).toBeDisabled();
  await page.getByLabel(/I inspected the exact prepared context/).check();
  await accept.click();
  await expect(page.getByRole("heading", { name: "Review the exact stored draft" })).toBeVisible();
  expect(submittedBody).toEqual({
    candidate_version: candidate.candidate_version,
    content_digest: candidate.content_digest,
    approval_attestation: true,
  });
  expect(submittedBody).not.toHaveProperty("general_relevance");
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
