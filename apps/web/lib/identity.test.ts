import { afterEach, describe, expect, it, vi } from "vitest";

import { authorizedHeaders, developmentAccessToken } from "./identity";

describe("development identity headers", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("uses an explicit development bearer without presenting it as production identity", () => {
    expect(developmentAccessToken).toBe("dev.local-browser");
    expect(authorizedHeaders({ Accept: "application/json" })).toEqual({
      Accept: "application/json",
      Authorization: "Bearer dev.local-browser",
    });
  });

  it("fails closed when an explicitly supplied token is blank", () => {
    expect(() => authorizedHeaders({}, " ")).toThrow("development access token");
  });

  it("leaves authorization server-side in production session mode", async () => {
    vi.stubEnv("NEXT_PUBLIC_AGAS_AUTH_MODE", "session");
    vi.resetModules();
    const sessionIdentity = await import("./identity");

    expect(sessionIdentity.browserAuthMode).toBe("session");
    expect(sessionIdentity.developmentAccessToken).toBe("");
    expect(sessionIdentity.reviewerDevelopmentAccessToken).toBe("");
    expect(sessionIdentity.assessmentReviewerDevelopmentAccessToken).toBe("");
    expect(sessionIdentity.authorizedHeaders({ Accept: "application/json" })).toEqual({
      Accept: "application/json",
    });
    expect(() =>
      sessionIdentity.authorizedHeaders({ Authorization: "Bearer browser-token" }),
    ).toThrow("cannot set authorization headers");
  });
});
