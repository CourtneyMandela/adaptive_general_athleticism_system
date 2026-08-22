import { describe, expect, it } from "vitest";

import { authorizedHeaders, developmentAccessToken } from "./identity";

describe("development identity headers", () => {
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
});
