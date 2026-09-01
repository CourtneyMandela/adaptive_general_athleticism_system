import { createHash, timingSafeEqual } from "node:crypto";
import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";

import { exportJWK, generateKeyPair, SignJWT } from "jose";

export const mockOidcIssuer = "http://127.0.0.1:3998/";
export const mockOidcClientId = "agas-e2e-client";
export const mockOidcClientSecret = "e2e-secret";
export const mockAccessToken = "agas-e2e-access-token";

const redirectUri = "http://127.0.0.1:3100/auth/callback";
const privateApiOrigin = "http://127.0.0.1:3999";
const maximumRequestBytes = 16_384;

type AuthorizationCode = Readonly<{
  challenge: string;
  clientId: string;
  nonce: string;
  redirectUri: string;
}>;

function json(response: ServerResponse, status: number, body: unknown): void {
  response.writeHead(status, {
    "cache-control": "no-store",
    "content-type": "application/json; charset=utf-8",
  });
  response.end(JSON.stringify(body));
}

function safeEqual(left: string, right: string): boolean {
  const leftBytes = Buffer.from(left);
  const rightBytes = Buffer.from(right);
  return leftBytes.length === rightBytes.length && timingSafeEqual(leftBytes, rightBytes);
}

async function requestBody(request: IncomingMessage): Promise<string> {
  const chunks: Buffer[] = [];
  let length = 0;
  for await (const chunk of request) {
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    length += bytes.length;
    if (length > maximumRequestBytes) throw new Error("request body is too large");
    chunks.push(bytes);
  }
  return Buffer.concat(chunks).toString("utf8");
}

function listen(server: Server, port: number): Promise<void> {
  return new Promise((resolve, reject) => {
    const onError = (error: Error) => reject(error);
    server.once("error", onError);
    server.listen(port, "127.0.0.1", () => {
      server.off("error", onError);
      resolve();
    });
  });
}

function close(server: Server): Promise<void> {
  return new Promise((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
}

export async function startMockServices(): Promise<{ close: () => Promise<void> }> {
  const { privateKey, publicKey } = await generateKeyPair("RS256");
  const publicJwk = {
    ...(await exportJWK(publicKey)),
    alg: "RS256",
    kid: "agas-e2e-key",
    use: "sig",
  };
  const codes = new Map<string, AuthorizationCode>();
  let sequence = 0;

  const oidc = createServer(async (request, response) => {
    try {
      const url = new URL(request.url ?? "/", mockOidcIssuer);
      if (request.method === "GET" && url.pathname === "/jwks") {
        json(response, 200, { keys: [publicJwk] });
        return;
      }

      if (request.method === "GET" && url.pathname === "/authorize") {
        const code = `agas-e2e-code-${++sequence}`;
        const record = {
          challenge: url.searchParams.get("code_challenge") ?? "",
          clientId: url.searchParams.get("client_id") ?? "",
          nonce: url.searchParams.get("nonce") ?? "",
          redirectUri: url.searchParams.get("redirect_uri") ?? "",
        };
        const valid =
          url.searchParams.get("response_type") === "code" &&
          record.clientId === mockOidcClientId &&
          record.redirectUri === redirectUri &&
          url.searchParams.get("code_challenge_method") === "S256" &&
          url.searchParams.get("scope") === "openid agas:api" &&
          url.searchParams.get("audience") === privateApiOrigin &&
          url.searchParams.get("resource") === privateApiOrigin &&
          record.challenge.length >= 43 &&
          record.nonce.length >= 16 &&
          (url.searchParams.get("state")?.length ?? 0) >= 16;
        if (!valid) {
          json(response, 400, { error: "invalid_request" });
          return;
        }
        codes.set(code, record);
        const callback = new URL(record.redirectUri);
        callback.searchParams.set("code", code);
        callback.searchParams.set("state", url.searchParams.get("state") ?? "");
        response.writeHead(303, { location: callback.toString() });
        response.end();
        return;
      }

      if (request.method === "POST" && url.pathname === "/token") {
        const expectedAuthorization = `Basic ${Buffer.from(
          `${mockOidcClientId}:${mockOidcClientSecret}`,
        ).toString("base64")}`;
        if (!safeEqual(request.headers.authorization ?? "", expectedAuthorization)) {
          json(response, 401, { error: "invalid_client" });
          return;
        }
        const form = new URLSearchParams(await requestBody(request));
        const code = form.get("code") ?? "";
        const record = codes.get(code);
        const verifier = form.get("code_verifier") ?? "";
        const actualChallenge = createHash("sha256").update(verifier).digest("base64url");
        const valid =
          record !== undefined &&
          form.get("grant_type") === "authorization_code" &&
          form.get("redirect_uri") === record.redirectUri &&
          form.get("resource") === privateApiOrigin &&
          verifier.length >= 43 &&
          safeEqual(actualChallenge, record.challenge);
        if (!valid || record === undefined) {
          json(response, 400, { error: "invalid_grant" });
          return;
        }
        codes.delete(code);
        const now = Math.floor(Date.now() / 1000);
        const idToken = await new SignJWT({ nonce: record.nonce })
          .setProtectedHeader({ alg: "RS256", kid: "agas-e2e-key", typ: "JWT" })
          .setIssuer(mockOidcIssuer)
          .setAudience(record.clientId)
          .setSubject("e2e-athlete-owner")
          .setIssuedAt(now)
          .setExpirationTime(now + 300)
          .sign(privateKey);
        json(response, 200, {
          access_token: mockAccessToken,
          expires_in: 300,
          id_token: idToken,
          token_type: "Bearer",
        });
        return;
      }

      json(response, 404, { error: "not_found" });
    } catch {
      json(response, 400, { error: "invalid_request" });
    }
  });

  const privateApi = createServer((request, response) => {
    const url = new URL(request.url ?? "/", privateApiOrigin);
    if (request.method !== "GET" || url.pathname !== "/v1/conformance/session") {
      json(response, 404, { detail: "Not found." });
      return;
    }
    if (
      request.headers.authorization !== `Bearer ${mockAccessToken}` ||
      request.headers.cookie !== undefined
    ) {
      json(response, 401, { detail: "Invalid forwarded credentials." });
      return;
    }
    json(response, 200, {
      authorization_received: true,
      subject: "e2e-athlete-owner",
    });
  });

  try {
    await listen(oidc, 3998);
    await listen(privateApi, 3999);
  } catch (error) {
    await Promise.allSettled([close(oidc), close(privateApi)]);
    throw error;
  }

  return {
    close: async () => {
      await Promise.all([close(oidc), close(privateApi)]);
    },
  };
}
