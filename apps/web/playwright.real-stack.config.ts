import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "real-stack.spec.ts",
  globalSetup: "./e2e/real-stack-global-setup.ts",
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:3101",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium-real-stack",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
