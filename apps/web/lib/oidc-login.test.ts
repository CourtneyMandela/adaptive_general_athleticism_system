import {
  SignJWT,
  base64url,
  createLocalJWKSet,
  exportJWK,
  generateKeyPair,
} from "jose";
import { describe, expect, it, vi } from "vitest";

import {
  OIDC_TRANSACTION_COOKIE_NAME,
  handleOidcCallback,
  handleOidcLogin,
  handleOidcLogout,
  verifyOidcIdTokenWithKey,
  type OidcEnvironment,
} from "./oidc-login";
import { SESSION_COOKIE_NAME, readServerSessionAccessToken } from "./server-session";

const now = 2_000_000_000;
const key = base64url.encode(new Uint8Array(32).fill(61));
const environment: OidcEnvironment = {
  AGAS_PUBLIC_WEB_ORIGIN: "https://app.agas.test",
  AGAS_SESSION_ENCRYPTION_KEY: key,
  AGAS_OIDC_ISSUER: "https://identity.test/",
  AGAS_OIDC_AUTHORIZATION_URL: "https://identity.test/oauth2/authorize",
  AGAS_OIDC_TOKEN_URL: "https://identity.test/oauth2/token",
  AGAS_OIDC_JWKS_URL: "https://identity.test/.well-known/jwks.json",
  AGAS_OIDC_CLIENT_ID: "agas-client",
  AGAS_OIDC_CLIENT_SECRET: "super-secret",
  AGAS_OIDC_SCOPES: "openid agas:api",
  AGAS_OIDC_RESOURCE: "https://api.agas.test",
  AGAS_OIDC_ID_TOKEN_ALGORITHMS: "RS256",
};

function deterministicRandom(): (size: number) => Uint8Array {
  let value = 1;
  return (size) => new Uint8Array(size).fill(value++);
}

function setCookieValue(response: Response, name: string): string {
  const combined = response.headers.get("set-cookie") ?? "";
  const match = new RegExp(`${name}=([^;,]*)`).exec(combined);
  if (!match) throw new Error(`Missing ${name} cookie.`);
  return decodeURIComponent(match[1] ?? "");
}

async function beginLogin(returnTo = "/"): Promise<{
  authorization: URL;
  transactionCookie: string;
}> {
  const response = await handleOidcLogin(
    new Request(
      `https://app.agas.test/auth/login?return_to=${encodeURIComponent(returnTo)}`,
    ),
    environment,
    deterministicRandom(),
    now,
  );
  return {
    authorization: new URL(response.headers.get("location") ?? ""),
    transactionCookie: `${OIDC_TRANSACTION_COOKIE_NAME}=${setCookieValue(
      response,
      OIDC_TRANSACTION_COOKIE_NAME,
    )}`,
  };
}

describe("provider-neutral OIDC browser login", () => {
  it("starts a bounded state, nonce, and S256 PKCE transaction", async () => {
    const response = await handleOidcLogin(
      new Request("https://app.agas.test/auth/login?return_to=%2Ftraining%3Fweek%3Dcurrent"),
      environment,
      deterministicRandom(),
      now,
    );

    expect(response.status).toBe(303);
    expect(response.headers.get("cache-control")).toBe("no-store");
    const authorization = new URL(response.headers.get("location") ?? "");
    expect(authorization.origin + authorization.pathname).toBe(
      "https://identity.test/oauth2/authorize",
    );
    expect(authorization.searchParams.get("response_type")).toBe("code");
    expect(authorization.searchParams.get("client_id")).toBe("agas-client");
    expect(authorization.searchParams.get("redirect_uri")).toBe(
      "https://app.agas.test/auth/callback",
    );
    expect(authorization.searchParams.get("scope")).toBe("openid agas:api");
    expect(authorization.searchParams.get("resource")).toBe("https://api.agas.test");
    expect(authorization.searchParams.get("state")).toHaveLength(43);
    expect(authorization.searchParams.get("nonce")).toHaveLength(43);
    expect(authorization.searchParams.get("code_challenge_method")).toBe("S256");
    expect(authorization.searchParams.get("code_challenge")).toHaveLength(43);
    const setCookie = response.headers.get("set-cookie") ?? "";
    expect(setCookie).toContain(`${OIDC_TRANSACTION_COOKIE_NAME}=`);
    expect(setCookie).toContain("Max-Age=600");
    expect(setCookie).toContain("Secure");
    expect(setCookie).toContain("HttpOnly");
    expect(setCookie).toContain("SameSite=Lax");
    expect(setCookie).not.toContain(authorization.searchParams.get("state") ?? "missing");
  });

  it("exchanges one callback code, verifies identity, and creates a bounded session", async () => {
    const { authorization, transactionCookie } = await beginLogin("/training?week=current");
    const verifier = vi.fn(async () => undefined);
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        access_token: "provider-access-token",
        expires_in: 7_200,
        id_token: "signed-id-token",
        token_type: "Bearer",
      }),
    );
    const callback = new URL("https://app.agas.test/auth/callback");
    callback.searchParams.set("code", "single-use-code");
    callback.searchParams.set("state", authorization.searchParams.get("state") ?? "");

    const response = await handleOidcCallback(
      new Request(callback, { headers: { Cookie: transactionCookie } }),
      fetcher,
      verifier,
      environment,
      now,
    );

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(
      "https://app.agas.test/training?week=current",
    );
    expect(fetcher).toHaveBeenCalledOnce();
    const [target, init] = fetcher.mock.calls[0] ?? [];
    expect(String(target)).toBe("https://identity.test/oauth2/token");
    expect(init).toMatchObject({ method: "POST", cache: "no-store", redirect: "manual" });
    const headers = new Headers(init?.headers);
    expect(headers.get("authorization")).toBe(
      `Basic ${Buffer.from("agas-client:super-secret").toString("base64")}`,
    );
    const body = new URLSearchParams(String(init?.body));
    expect(body.get("grant_type")).toBe("authorization_code");
    expect(body.get("code")).toBe("single-use-code");
    expect(body.get("redirect_uri")).toBe("https://app.agas.test/auth/callback");
    expect(body.get("code_verifier")).toHaveLength(86);
    expect(body.get("resource")).toBe("https://api.agas.test");
    expect(verifier).toHaveBeenCalledWith(
      "signed-id-token",
      expect.objectContaining({ clientId: "agas-client", issuer: "https://identity.test/" }),
      authorization.searchParams.get("nonce"),
      now,
    );

    const session = setCookieValue(response, SESSION_COOKIE_NAME);
    await expect(
      readServerSessionAccessToken(`${SESSION_COOKIE_NAME}=${session}`, key, now + 3_599),
    ).resolves.toBe("provider-access-token");
    await expect(
      readServerSessionAccessToken(`${SESSION_COOKIE_NAME}=${session}`, key, now + 3_600),
    ).resolves.toBeNull();
    const setCookie = response.headers.get("set-cookie") ?? "";
    expect(setCookie).toContain(`${OIDC_TRANSACTION_COOKIE_NAME}=;`);
    expect(setCookie).toContain(`${SESSION_COOKIE_NAME}=`);
    expect(setCookie).toContain("Max-Age=3600");
    expect(setCookie).toContain("Secure");
    expect(setCookie).toContain("HttpOnly");
    expect(setCookie).toContain("SameSite=Lax");
    expect(setCookie).not.toContain("provider-access-token");
  });

  it("rejects callback mismatch and provider errors without contacting or creating a session", async () => {
    const { transactionCookie } = await beginLogin();
    const fetcher = vi.fn<typeof fetch>();
    const mismatch = await handleOidcCallback(
      new Request("https://app.agas.test/auth/callback?code=code&state=wrong", {
        headers: { Cookie: transactionCookie },
      }),
      fetcher,
      vi.fn(async () => undefined),
      environment,
      now,
    );
    const providerError = await handleOidcCallback(
      new Request("https://app.agas.test/auth/callback?error=access_denied", {
        headers: { Cookie: transactionCookie },
      }),
      fetcher,
      vi.fn(async () => undefined),
      environment,
      now,
    );

    expect(mismatch.status).toBe(400);
    expect(providerError.status).toBe(400);
    expect(fetcher).not.toHaveBeenCalled();
    expect(mismatch.headers.get("set-cookie")).toContain(
      `${OIDC_TRANSACTION_COOKIE_NAME}=;`,
    );
    expect(mismatch.headers.get("set-cookie")).not.toContain(`${SESSION_COOKIE_NAME}=`);
  });

  it("rejects an invalid identity token and clears only the transaction", async () => {
    const { authorization, transactionCookie } = await beginLogin();
    const callback = new URL("https://app.agas.test/auth/callback");
    callback.searchParams.set("code", "code");
    callback.searchParams.set("state", authorization.searchParams.get("state") ?? "");
    const response = await handleOidcCallback(
      new Request(callback, { headers: { Cookie: transactionCookie } }),
      vi.fn<typeof fetch>(async () =>
        Response.json({
          access_token: "provider-access-token",
          expires_in: 300,
          id_token: "invalid",
          token_type: "Bearer",
        }),
      ),
      vi.fn(async () => {
        throw new Error("signature failure");
      }),
      environment,
      now,
    );

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({
      detail: "Identity provider returned an invalid identity token.",
    });
    expect(response.headers.get("set-cookie")).not.toContain(`${SESSION_COOKIE_NAME}=`);
  });

  it("rejects stale transactions and malformed token lifetimes", async () => {
    const first = await beginLogin();
    const staleUrl = new URL("https://app.agas.test/auth/callback");
    staleUrl.searchParams.set("code", "code");
    staleUrl.searchParams.set("state", first.authorization.searchParams.get("state") ?? "");
    const fetcher = vi.fn<typeof fetch>();
    const stale = await handleOidcCallback(
      new Request(staleUrl, { headers: { Cookie: first.transactionCookie } }),
      fetcher,
      vi.fn(async () => undefined),
      environment,
      now + 600,
    );

    const second = await beginLogin();
    const malformedUrl = new URL("https://app.agas.test/auth/callback");
    malformedUrl.searchParams.set("code", "code");
    malformedUrl.searchParams.set("state", second.authorization.searchParams.get("state") ?? "");
    const verifier = vi.fn(async () => undefined);
    const malformed = await handleOidcCallback(
      new Request(malformedUrl, { headers: { Cookie: second.transactionCookie } }),
      vi.fn<typeof fetch>(async () =>
        Response.json({
          access_token: "provider-access-token",
          expires_in: "300",
          id_token: "signed-id-token",
          token_type: "Bearer",
        }),
      ),
      verifier,
      environment,
      now,
    );

    expect(stale.status).toBe(400);
    expect(fetcher).not.toHaveBeenCalled();
    expect(malformed.status).toBe(502);
    expect(verifier).not.toHaveBeenCalled();
  });

  it("cryptographically verifies issuer, audience, timestamps, subject, and nonce", async () => {
    const { privateKey, publicKey } = await generateKeyPair("RS256");
    const jwk = await exportJWK(publicKey);
    const localJwks = createLocalJWKSet({
      keys: [{ ...jwk, alg: "RS256", kid: "test-key", use: "sig" }],
    });
    const token = await new SignJWT({ nonce: "expected-nonce" })
      .setProtectedHeader({ alg: "RS256", kid: "test-key" })
      .setIssuer("https://identity.test/")
      .setAudience("agas-client")
      .setSubject("provider-subject")
      .setIssuedAt(now)
      .setExpirationTime(now + 300)
      .sign(privateKey);

    await expect(
      verifyOidcIdTokenWithKey(
        token,
        {
          issuer: "https://identity.test/",
          audience: "agas-client",
          algorithms: ["RS256"],
          nonce: "expected-nonce",
        },
        localJwks,
        now,
      ),
    ).resolves.toBeUndefined();
    await expect(
      verifyOidcIdTokenWithKey(
        token,
        {
          issuer: "https://identity.test/",
          audience: "agas-client",
          algorithms: ["RS256"],
          nonce: "wrong-nonce",
        },
        localJwks,
        now,
      ),
    ).rejects.toThrow("invalid");
  });

  it("fails closed for unsafe configuration and external return paths", async () => {
    const unsafeProvider = await handleOidcLogin(
      new Request("https://app.agas.test/auth/login"),
      { ...environment, AGAS_OIDC_ISSUER: "http://identity.test" },
      deterministicRandom(),
      now,
    );
    const externalReturn = await handleOidcLogin(
      new Request("https://app.agas.test/auth/login?return_to=https%3A%2F%2Fattacker.test"),
      environment,
      deterministicRandom(),
      now,
    );

    expect(unsafeProvider.status).toBe(503);
    expect(externalReturn.status).toBe(400);
  });

  it("logs out only from a same-origin POST and clears both local cookies", () => {
    const rejected = handleOidcLogout(
      new Request("https://app.agas.test/auth/logout", {
        method: "POST",
        headers: { Origin: "https://attacker.test" },
      }),
      environment,
    );
    const accepted = handleOidcLogout(
      new Request("https://app.agas.test/auth/logout", {
        method: "POST",
        headers: {
          Origin: "https://app.agas.test",
          "Sec-Fetch-Site": "same-origin",
        },
      }),
      environment,
    );

    expect(rejected.status).toBe(403);
    expect(accepted.status).toBe(303);
    expect(accepted.headers.get("location")).toBe("https://app.agas.test/");
    const setCookie = accepted.headers.get("set-cookie") ?? "";
    expect(setCookie).toContain(`${OIDC_TRANSACTION_COOKIE_NAME}=;`);
    expect(setCookie).toContain(`${SESSION_COOKIE_NAME}=;`);
    expect(setCookie).toContain("Max-Age=0");
  });
});
