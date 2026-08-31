import { base64url } from "jose";
import { describe, expect, it } from "vitest";

import {
  SESSION_COOKIE_NAME,
  SessionConfigurationError,
  readServerSessionAccessToken,
  sealServerSession,
} from "./server-session";

const key = base64url.encode(new Uint8Array(32).fill(17));
const otherKey = base64url.encode(new Uint8Array(32).fill(23));

describe("encrypted server session", () => {
  it("round-trips a short-lived access token without exposing plaintext", async () => {
    const sealed = await sealServerSession("provider-access-token", 200, key, 100);

    expect(sealed).not.toContain("provider-access-token");
    await expect(
      readServerSessionAccessToken(`${SESSION_COOKIE_NAME}=${sealed}`, key, 150),
    ).resolves.toBe("provider-access-token");
  });

  it("rejects expiry, tampering, a wrong key, and ambiguous cookies", async () => {
    const sealed = await sealServerSession("provider-access-token", 200, key, 100);
    const tamperedParts = sealed.split(".");
    const ciphertext = tamperedParts[3] ?? "";
    tamperedParts[3] = `${ciphertext.startsWith("a") ? "b" : "a"}${ciphertext.slice(1)}`;
    const tampered = tamperedParts.join(".");

    await expect(
      readServerSessionAccessToken(`${SESSION_COOKIE_NAME}=${sealed}`, key, 200),
    ).resolves.toBeNull();
    await expect(
      readServerSessionAccessToken(`${SESSION_COOKIE_NAME}=${tampered}`, key, 150),
    ).resolves.toBeNull();
    await expect(
      readServerSessionAccessToken(`${SESSION_COOKIE_NAME}=${sealed}`, otherKey, 150),
    ).resolves.toBeNull();
    await expect(
      readServerSessionAccessToken(
        `${SESSION_COOKIE_NAME}=${sealed}; ${SESSION_COOKIE_NAME}=${sealed}`,
        key,
        150,
      ),
    ).resolves.toBeNull();
  });

  it("fails closed for missing or malformed server-only key material", async () => {
    await expect(readServerSessionAccessToken(null, undefined, 100)).rejects.toBeInstanceOf(
      SessionConfigurationError,
    );
    await expect(readServerSessionAccessToken(null, "not-base64!", 100)).rejects.toBeInstanceOf(
      SessionConfigurationError,
    );
    await expect(
      readServerSessionAccessToken(null, base64url.encode(new Uint8Array(31)), 100),
    ).rejects.toBeInstanceOf(SessionConfigurationError);
  });

  it("will not seal a blank or already expired session", async () => {
    await expect(sealServerSession(" ", 200, key, 100)).rejects.toThrow("non-empty access token");
    await expect(sealServerSession("token", 100, key, 100)).rejects.toThrow("future expiry");
  });
});
