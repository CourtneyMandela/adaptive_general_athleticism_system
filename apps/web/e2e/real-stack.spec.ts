import { expect, test } from "@playwright/test";

test("a signed-in owner creates and recovers a persisted profile through the real API", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in to open your training." })).toBeVisible();

  const signInLinks = page.getByRole("link", { name: "Sign in securely" });
  await expect(signInLinks).toHaveCount(2);
  const trainingSignIn = page
    .getByLabel("Sign in to open your training.")
    .getByRole("link", { name: "Sign in securely" });
  await expect(trainingSignIn).toHaveAttribute("href", "/auth/login?return_to=%2F");
  await trainingSignIn.click();
  await expect(page).toHaveURL("http://127.0.0.1:3101/");
  await expect(page.getByText("Secure session active")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Start with what you know." })).toBeVisible();

  await page.getByLabel("Display name").fill("Real-stack owner");
  await page.getByLabel("Training goals").fill("Build broad athletic capacity");
  await page.getByLabel(/Activities you enjoy/).fill("Hiking");
  await page.getByLabel("Usable floor area, m²").fill("10");
  await page.getByLabel("Outdoor training is available here").check();
  await page.getByRole("button", { name: "Create profile" }).click();

  await expect(page.getByRole("heading", { name: "Real-stack owner" })).toBeVisible();
  await expect(page.getByText(/There is no persisted plan covering/)).toBeVisible();
  await expect(
    page.getByText("Your profile is saved; AGAS still owes you the training path."),
  ).toBeVisible();

  await page.reload();
  await expect(page.getByText("Secure session active")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Real-stack owner" })).toBeVisible();
  await expect(page.getByText(/There is no persisted plan covering/)).toBeVisible();
});
