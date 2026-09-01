import { base64url } from "jose";
import { describe, expect, it, vi } from "vitest";

import { handleApiGateway } from "./api-gateway";
import { SESSION_COOKIE_NAME, sealServerSession } from "./server-session";

const key = base64url.encode(new Uint8Array(32).fill(41));
const environment = {
  AGAS_INTERNAL_API_URL: "http://api:8000",
  AGAS_PUBLIC_WEB_ORIGIN: "https://app.agas.test",
  AGAS_SESSION_ENCRYPTION_KEY: key,
};

async function sessionCookie(): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  const sealed = await sealServerSession("provider-access-token", now + 300, key, now);
  return `${SESSION_COOKIE_NAME}=${sealed}`;
}

describe("same-origin API gateway", () => {
  it("accepts one platform-provided private host and port without making FastAPI public", async () => {
    const fetcher = vi.fn<typeof fetch>(async () => Response.json({ ok: true }));
    const response = await handleApiGateway(
      new Request("https://app.agas.test/api/agas/v1/health", {
        headers: { Cookie: await sessionCookie() },
      }),
      ["v1", "health"],
      fetcher,
      {
        AGAS_INTERNAL_API_HOSTPORT: "agas-api-staging:8000",
        AGAS_PUBLIC_WEB_ORIGIN: environment.AGAS_PUBLIC_WEB_ORIGIN,
        AGAS_SESSION_ENCRYPTION_KEY: key,
      },
    );

    expect(response.status).toBe(200);
    expect(String(fetcher.mock.calls[0]?.[0])).toBe("http://agas-api-staging:8000/v1/health");
  });

  it("fails closed when private API configuration is ambiguous", async () => {
    const fetcher = vi.fn<typeof fetch>();
    const response = await handleApiGateway(
      new Request("https://app.agas.test/api/agas/v1/health", {
        headers: { Cookie: await sessionCookie() },
      }),
      ["v1", "health"],
      fetcher,
      { ...environment, AGAS_INTERNAL_API_HOSTPORT: "other-api:8000" },
    );

    expect(response.status).toBe(503);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("requires a configured encrypted session before contacting FastAPI", async () => {
    const fetcher = vi.fn<typeof fetch>();
    const response = await handleApiGateway(
      new Request("https://app.agas.test/api/agas/v1/onboarding/athletes"),
      ["v1", "onboarding", "athletes"],
      fetcher,
      environment,
    );

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: "Authentication is required." });
    expect(fetcher).not.toHaveBeenCalled();
    expect(response.headers.get("cache-control")).toBe("no-store");
  });

  it("forwards only selected headers and a server-owned bearer to the private API", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json(
        { athlete_id: "athlete-1" },
        {
          headers: {
            ETag: '"projection-1"',
            "Set-Cookie": "upstream=must-not-reach-browser",
            "X-Internal-Debug": "private",
          },
        },
      ),
    );
    const response = await handleApiGateway(
      new Request("https://app.agas.test/api/agas/v1/athletes/athlete-1/current-week?on=2026-08-31", {
        headers: {
          Accept: "application/json",
          Cookie: await sessionCookie(),
          "X-Internal-Debug": "browser-value",
        },
      }),
      ["v1", "athletes", "athlete-1", "current-week"],
      fetcher,
      environment,
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("etag")).toBe('"projection-1"');
    expect(response.headers.get("set-cookie")).toBeNull();
    expect(response.headers.get("x-internal-debug")).toBeNull();
    const [target, init] = fetcher.mock.calls[0] ?? [];
    expect(String(target)).toBe(
      "http://api:8000/v1/athletes/athlete-1/current-week?on=2026-08-31",
    );
    const headers = new Headers(init?.headers);
    expect(headers.get("authorization")).toBe("Bearer provider-access-token");
    expect(headers.get("accept")).toBe("application/json");
    expect(headers.get("cookie")).toBeNull();
    expect(headers.get("x-internal-debug")).toBeNull();
    expect(init).toMatchObject({ cache: "no-store", method: "GET", redirect: "manual" });
  });

  it("forwards bounded same-origin JSON writes", async () => {
    const fetcher = vi.fn<typeof fetch>(async (_input, init) =>
      Response.json({ received: await new Response(init?.body).json() }, { status: 201 }),
    );
    const response = await handleApiGateway(
      new Request("https://app.agas.test/api/agas/v1/onboarding/athletes", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Cookie: await sessionCookie(),
          Origin: "https://app.agas.test",
          "Sec-Fetch-Site": "same-origin",
        },
        body: JSON.stringify({ display_name: "Athlete" }),
      }),
      ["v1", "onboarding", "athletes"],
      fetcher,
      environment,
    );

    expect(response.status).toBe(201);
    await expect(response.json()).resolves.toEqual({ received: { display_name: "Athlete" } });
  });

  it("rejects cross-origin writes, traversal segments, and oversized bodies", async () => {
    const fetcher = vi.fn<typeof fetch>();
    const cookie = await sessionCookie();
    const crossOrigin = await handleApiGateway(
      new Request("https://app.agas.test/api/agas/v1/onboarding/athletes", {
        method: "POST",
        headers: { Cookie: cookie, Origin: "https://attacker.test" },
        body: "{}",
      }),
      ["v1", "onboarding", "athletes"],
      fetcher,
      environment,
    );
    const traversal = await handleApiGateway(
      new Request("https://app.agas.test/api/agas/admin"),
      ["v1", "..", "admin"],
      fetcher,
      environment,
    );
    const oversized = await handleApiGateway(
      new Request("https://app.agas.test/api/agas/v1/onboarding/athletes", {
        method: "POST",
        headers: {
          "Content-Length": "1048577",
          Cookie: cookie,
          Origin: "https://app.agas.test",
        },
        body: "{}",
      }),
      ["v1", "onboarding", "athletes"],
      fetcher,
      environment,
    );
    const streamedOversized = await handleApiGateway(
      new Request("https://app.agas.test/api/agas/v1/onboarding/athletes", {
        method: "POST",
        headers: {
          Cookie: cookie,
          Origin: "https://app.agas.test",
        },
        body: new Uint8Array(1_048_577),
      }),
      ["v1", "onboarding", "athletes"],
      fetcher,
      environment,
    );

    expect(crossOrigin.status).toBe(403);
    expect(traversal.status).toBe(404);
    expect(oversized.status).toBe(413);
    expect(streamedOversized.status).toBe(413);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("distinguishes unavailable configuration from an unavailable upstream", async () => {
    const request = new Request("https://app.agas.test/api/agas/v1/athletes", {
      headers: { Cookie: await sessionCookie() },
    });
    const notConfigured = await handleApiGateway(request.clone(), ["v1", "athletes"], fetch, {
      ...environment,
      AGAS_SESSION_ENCRYPTION_KEY: undefined,
    });
    const insecurePublicOrigin = await handleApiGateway(
      request.clone(),
      ["v1", "athletes"],
      fetch,
      {
        ...environment,
        AGAS_PUBLIC_WEB_ORIGIN: "http://app.agas.test",
      },
    );
    const unavailable = await handleApiGateway(
      request,
      ["v1", "athletes"],
      vi.fn<typeof fetch>(async () => {
        throw new Error("private detail");
      }),
      environment,
    );

    expect(notConfigured.status).toBe(503);
    expect(insecurePublicOrigin.status).toBe(503);
    await expect(notConfigured.json()).resolves.toEqual({
      detail: "Browser session service is unavailable.",
    });
    expect(unavailable.status).toBe(502);
    await expect(unavailable.json()).resolves.toEqual({
      detail: "Athlete data service is unavailable.",
    });
  });
});
