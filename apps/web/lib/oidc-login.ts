import { randomBytes, timingSafeEqual } from "node:crypto";

import {
  base64url,
  CompactEncrypt,
  compactDecrypt,
  createRemoteJWKSet,
  jwtVerify,
  type JWTVerifyGetKey,
  type RemoteJWKSet,
} from "jose";

import {
  SESSION_COOKIE_NAME,
  SessionConfigurationError,
  sealServerSession,
  sessionEncryptionKey,
} from "./server-session";

export const OIDC_TRANSACTION_COOKIE_NAME = "__Host-agas-oidc";
export const OIDC_TRANSACTION_VERSION = 1;

const TRANSACTION_LIFETIME_SECONDS = 600;
const MAX_SESSION_SECONDS = 3_600;
const TOKEN_TIMEOUT_MS = 10_000;
const MAX_TOKEN_RESPONSE_BYTES = 65_536;
const encoder = new TextEncoder();
const decoder = new TextDecoder();
const allowedIdTokenAlgorithms = new Set(["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]);

export type OidcEnvironment = Readonly<{
  AGAS_PUBLIC_WEB_ORIGIN?: string;
  AGAS_SESSION_ENCRYPTION_KEY?: string;
  AGAS_OIDC_ISSUER?: string;
  AGAS_OIDC_AUTHORIZATION_URL?: string;
  AGAS_OIDC_TOKEN_URL?: string;
  AGAS_OIDC_JWKS_URL?: string;
  AGAS_OIDC_CLIENT_ID?: string;
  AGAS_OIDC_CLIENT_SECRET?: string;
  AGAS_OIDC_SCOPES?: string;
  AGAS_OIDC_AUDIENCE?: string;
  AGAS_OIDC_RESOURCE?: string;
  AGAS_OIDC_ID_TOKEN_ALGORITHMS?: string;
}>;

type OidcConfig = Readonly<{
  publicOrigin: URL;
  issuer: string;
  authorizationUrl: URL;
  tokenUrl: URL;
  jwksUrl: URL;
  clientId: string;
  clientSecret: string;
  scopes: readonly string[];
  audience?: string;
  resource?: string;
  idTokenAlgorithms: readonly string[];
}>;

type OidcTransaction = Readonly<{
  version: typeof OIDC_TRANSACTION_VERSION;
  state: string;
  nonce: string;
  code_verifier: string;
  return_to: string;
  expires_at: number;
}>;

type VerifyIdToken = (
  idToken: string,
  config: OidcConfig,
  expectedNonce: string,
  nowEpochSeconds: number,
) => Promise<void>;

export class OidcConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "OidcConfigurationError";
  }
}

function currentEnvironment(): OidcEnvironment {
  return {
    AGAS_PUBLIC_WEB_ORIGIN: process.env.AGAS_PUBLIC_WEB_ORIGIN,
    AGAS_SESSION_ENCRYPTION_KEY: process.env.AGAS_SESSION_ENCRYPTION_KEY,
    AGAS_OIDC_ISSUER: process.env.AGAS_OIDC_ISSUER,
    AGAS_OIDC_AUTHORIZATION_URL: process.env.AGAS_OIDC_AUTHORIZATION_URL,
    AGAS_OIDC_TOKEN_URL: process.env.AGAS_OIDC_TOKEN_URL,
    AGAS_OIDC_JWKS_URL: process.env.AGAS_OIDC_JWKS_URL,
    AGAS_OIDC_CLIENT_ID: process.env.AGAS_OIDC_CLIENT_ID,
    AGAS_OIDC_CLIENT_SECRET: process.env.AGAS_OIDC_CLIENT_SECRET,
    AGAS_OIDC_SCOPES: process.env.AGAS_OIDC_SCOPES,
    AGAS_OIDC_AUDIENCE: process.env.AGAS_OIDC_AUDIENCE,
    AGAS_OIDC_RESOURCE: process.env.AGAS_OIDC_RESOURCE,
    AGAS_OIDC_ID_TOKEN_ALGORITHMS: process.env.AGAS_OIDC_ID_TOKEN_ALGORITHMS,
  };
}

function requiredValue(value: string | undefined, label: string, maximum = 4_096): string {
  const normalized = value?.trim();
  if (!normalized) throw new OidcConfigurationError(`${label} is not configured.`);
  if (normalized.length > maximum || /[\u0000-\u001f\u007f]/u.test(normalized)) {
    throw new OidcConfigurationError(`${label} is invalid.`);
  }
  return normalized;
}

function secureUrl(value: string | undefined, label: string, originOnly = false): URL {
  const normalized = requiredValue(value, label, 2_048);
  let url: URL;
  try {
    url = new URL(normalized);
  } catch {
    throw new OidcConfigurationError(`${label} is invalid.`);
  }
  if (!new Set(["http:", "https:"]).has(url.protocol) || url.username || url.password) {
    throw new OidcConfigurationError(`${label} must be an HTTP(S) URL without credentials.`);
  }
  const loopback = new Set(["localhost", "127.0.0.1", "[::1]"]).has(url.hostname);
  if (url.protocol !== "https:" && !loopback) {
    throw new OidcConfigurationError(`${label} must use HTTPS outside local development.`);
  }
  if (url.hash || (originOnly && (url.pathname !== "/" || url.search))) {
    throw new OidcConfigurationError(
      originOnly ? `${label} must be an origin.` : `${label} must not contain a fragment.`,
    );
  }
  return url;
}

function oidcConfig(environment: OidcEnvironment): OidcConfig {
  const scopes = requiredValue(environment.AGAS_OIDC_SCOPES, "OIDC scopes", 1_024)
    .split(/\s+/u)
    .filter((scope, index, all) => all.indexOf(scope) === index);
  if (!scopes.includes("openid") || scopes.some((scope) => !/^[\x21-\x7e]+$/u.test(scope))) {
    throw new OidcConfigurationError("OIDC scopes must be printable tokens including openid.");
  }

  const idTokenAlgorithms = requiredValue(
    environment.AGAS_OIDC_ID_TOKEN_ALGORITHMS,
    "OIDC ID-token algorithms",
    256,
  )
    .split(",")
    .map((algorithm) => algorithm.trim())
    .filter((algorithm, index, all) => algorithm && all.indexOf(algorithm) === index);
  if (
    idTokenAlgorithms.length === 0 ||
    idTokenAlgorithms.some((algorithm) => !allowedIdTokenAlgorithms.has(algorithm))
  ) {
    throw new OidcConfigurationError("OIDC ID-token algorithms must use the asymmetric allow-list.");
  }

  const audience = environment.AGAS_OIDC_AUDIENCE?.trim();
  if (audience && !/^[\x21-\x7e]+$/u.test(requiredValue(audience, "OIDC audience", 2_048))) {
    throw new OidcConfigurationError("OIDC audience must be one printable token.");
  }
  const resource = environment.AGAS_OIDC_RESOURCE?.trim();
  if (resource) secureUrl(resource, "OIDC resource");
  const issuer = secureUrl(environment.AGAS_OIDC_ISSUER, "OIDC issuer");
  if (issuer.search) {
    throw new OidcConfigurationError("OIDC issuer must not contain a query.");
  }

  return {
    publicOrigin: secureUrl(environment.AGAS_PUBLIC_WEB_ORIGIN, "Public web origin", true),
    issuer: issuer.toString(),
    authorizationUrl: secureUrl(
      environment.AGAS_OIDC_AUTHORIZATION_URL,
      "OIDC authorization URL",
    ),
    tokenUrl: secureUrl(environment.AGAS_OIDC_TOKEN_URL, "OIDC token URL"),
    jwksUrl: secureUrl(environment.AGAS_OIDC_JWKS_URL, "OIDC JWKS URL"),
    clientId: requiredValue(environment.AGAS_OIDC_CLIENT_ID, "OIDC client ID", 512),
    clientSecret: requiredValue(environment.AGAS_OIDC_CLIENT_SECRET, "OIDC client secret"),
    scopes,
    audience: audience || undefined,
    resource: resource || undefined,
    idTokenAlgorithms,
  };
}

function cookieValue(cookieHeader: string | null, name: string): string | null {
  if (!cookieHeader) return null;
  const matches = cookieHeader
    .split(";")
    .map((part) => part.trim())
    .filter((part) => part.startsWith(`${name}=`))
    .map((part) => part.slice(name.length + 1));
  if (matches.length !== 1 || !matches[0]) return null;
  try {
    return decodeURIComponent(matches[0]);
  } catch {
    return null;
  }
}

function secureCookie(name: string, value: string, maxAgeSeconds: number): string {
  return `${name}=${encodeURIComponent(value)}; Path=/; Max-Age=${maxAgeSeconds}; Secure; HttpOnly; SameSite=Lax`;
}

function clearCookie(name: string): string {
  return secureCookie(name, "", 0);
}

function errorResponse(status: number, detail: string, clearTransaction = false): Response {
  const headers = new Headers({ "Cache-Control": "no-store" });
  if (clearTransaction) headers.append("Set-Cookie", clearCookie(OIDC_TRANSACTION_COOKIE_NAME));
  return Response.json({ detail }, { status, headers });
}

function validReturnPath(value: string | null): string | null {
  if (value === null || value === "") return "/";
  if (
    value.length > 2_048 ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.includes("\\") ||
    /[\u0000-\u001f\u007f]/u.test(value)
  ) {
    return null;
  }
  return value;
}

function transactionEnvelope(value: unknown, nowEpochSeconds: number): OidcTransaction | null {
  if (typeof value !== "object" || value === null) return null;
  const candidate = value as Partial<OidcTransaction>;
  if (
    candidate.version !== OIDC_TRANSACTION_VERSION ||
    typeof candidate.state !== "string" ||
    candidate.state.length < 32 ||
    typeof candidate.nonce !== "string" ||
    candidate.nonce.length < 32 ||
    typeof candidate.code_verifier !== "string" ||
    candidate.code_verifier.length < 43 ||
    candidate.code_verifier.length > 128 ||
    typeof candidate.return_to !== "string" ||
    validReturnPath(candidate.return_to) === null ||
    !Number.isInteger(candidate.expires_at) ||
    (candidate.expires_at ?? 0) <= nowEpochSeconds
  ) {
    return null;
  }
  return candidate as OidcTransaction;
}

async function sealTransaction(
  transaction: OidcTransaction,
  encodedKey: string | undefined,
): Promise<string> {
  return new CompactEncrypt(encoder.encode(JSON.stringify(transaction)))
    .setProtectedHeader({ alg: "dir", enc: "A256GCM", typ: "agas-oidc-transaction+jwe" })
    .encrypt(sessionEncryptionKey(encodedKey));
}

async function readTransaction(
  cookieHeader: string | null,
  encodedKey: string | undefined,
  nowEpochSeconds: number,
): Promise<OidcTransaction | null> {
  const key = sessionEncryptionKey(encodedKey);
  const encrypted = cookieValue(cookieHeader, OIDC_TRANSACTION_COOKIE_NAME);
  if (encrypted === null) return null;
  try {
    const { plaintext, protectedHeader } = await compactDecrypt(encrypted, key, {
      contentEncryptionAlgorithms: ["A256GCM"],
      keyManagementAlgorithms: ["dir"],
    });
    if (
      protectedHeader.alg !== "dir" ||
      protectedHeader.enc !== "A256GCM" ||
      protectedHeader.typ !== "agas-oidc-transaction+jwe"
    ) {
      return null;
    }
    return transactionEnvelope(JSON.parse(decoder.decode(plaintext)) as unknown, nowEpochSeconds);
  } catch {
    return null;
  }
}

function safeEqual(left: string, right: string): boolean {
  const leftBytes = Buffer.from(left);
  const rightBytes = Buffer.from(right);
  return leftBytes.byteLength === rightBytes.byteLength && timingSafeEqual(leftBytes, rightBytes);
}

function randomBase64Url(size: number, random: (size: number) => Uint8Array): string {
  return base64url.encode(random(size));
}

function redirectUri(config: OidcConfig): string {
  return new URL("/auth/callback", config.publicOrigin).toString();
}

function formEncodedCredential(value: string): string {
  return new URLSearchParams({ value }).toString().slice("value=".length);
}

function clientAuthorization(config: OidcConfig): string {
  const credentials = `${formEncodedCredential(config.clientId)}:${formEncodedCredential(config.clientSecret)}`;
  return `Basic ${Buffer.from(credentials).toString("base64")}`;
}

async function boundedText(response: Response): Promise<string | null> {
  const declaredLength = response.headers.get("content-length");
  if (declaredLength !== null) {
    const parsed = Number(declaredLength);
    if (!Number.isFinite(parsed) || parsed < 0 || parsed > MAX_TOKEN_RESPONSE_BYTES) return null;
  }
  if (response.body === null) return "";
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > MAX_TOKEN_RESPONSE_BYTES) {
      await reader.cancel();
      return null;
    }
    chunks.push(value);
  }
  const body = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return decoder.decode(body);
}

function tokenResponse(value: unknown): {
  accessToken: string;
  expiresIn: number;
  idToken: string;
} | null {
  if (typeof value !== "object" || value === null) return null;
  const candidate = value as Record<string, unknown>;
  if (
    typeof candidate.access_token !== "string" ||
    !candidate.access_token.trim() ||
    typeof candidate.id_token !== "string" ||
    !candidate.id_token.trim() ||
    typeof candidate.token_type !== "string" ||
    candidate.token_type.toLowerCase() !== "bearer" ||
    typeof candidate.expires_in !== "number" ||
    !Number.isSafeInteger(candidate.expires_in) ||
    candidate.expires_in <= 0
  ) {
    return null;
  }
  return {
    accessToken: candidate.access_token,
    expiresIn: candidate.expires_in,
    idToken: candidate.id_token,
  };
}

const remoteJwks = new Map<string, RemoteJWKSet>();

export async function verifyOidcIdTokenWithKey(
  idToken: string,
  expectations: Readonly<{
    issuer: string;
    audience: string;
    algorithms: readonly string[];
    nonce: string;
  }>,
  key: JWTVerifyGetKey,
  nowEpochSeconds: number,
): Promise<void> {
  const { payload } = await jwtVerify(idToken, key, {
    algorithms: [...expectations.algorithms],
    audience: expectations.audience,
    issuer: expectations.issuer,
    clockTolerance: 30,
    currentDate: new Date(nowEpochSeconds * 1_000),
    maxTokenAge: "5 minutes",
    requiredClaims: ["exp", "iat", "iss", "aud", "sub", "nonce"],
  });
  if (
    typeof payload.sub !== "string" ||
    !payload.sub.trim() ||
    typeof payload.nonce !== "string" ||
    !safeEqual(payload.nonce, expectations.nonce)
  ) {
    throw new Error("OIDC ID token is invalid.");
  }
}

async function verifyOidcIdToken(
  idToken: string,
  config: OidcConfig,
  expectedNonce: string,
  nowEpochSeconds: number,
): Promise<void> {
  let jwks = remoteJwks.get(config.jwksUrl.toString());
  if (!jwks) {
    jwks = createRemoteJWKSet(config.jwksUrl, {
      timeoutDuration: TOKEN_TIMEOUT_MS,
      cooldownDuration: 30_000,
      cacheMaxAge: 300_000,
    });
    remoteJwks.set(config.jwksUrl.toString(), jwks);
  }
  await verifyOidcIdTokenWithKey(
    idToken,
    {
      issuer: config.issuer,
      audience: config.clientId,
      algorithms: config.idTokenAlgorithms,
      nonce: expectedNonce,
    },
    jwks,
    nowEpochSeconds,
  );
}

export async function handleOidcLogin(
  request: Request,
  environment: OidcEnvironment = currentEnvironment(),
  random: (size: number) => Uint8Array = randomBytes,
  nowEpochSeconds = Math.floor(Date.now() / 1_000),
): Promise<Response> {
  let config: OidcConfig;
  try {
    config = oidcConfig(environment);
    sessionEncryptionKey(environment.AGAS_SESSION_ENCRYPTION_KEY);
  } catch (error) {
    if (error instanceof OidcConfigurationError || error instanceof SessionConfigurationError) {
      return errorResponse(503, "Login service is unavailable.");
    }
    return errorResponse(500, "Unable to start login.");
  }

  const requestUrl = new URL(request.url);
  const returnValues = requestUrl.searchParams.getAll("return_to");
  const returnTo = validReturnPath(returnValues.length === 0 ? null : returnValues[0] ?? null);
  if (returnValues.length > 1 || returnTo === null) {
    return errorResponse(400, "Login return path is invalid.");
  }

  let state: string;
  let nonce: string;
  let codeVerifier: string;
  let challenge: string;
  let transaction: string;
  try {
    state = randomBase64Url(32, random);
    nonce = randomBase64Url(32, random);
    codeVerifier = randomBase64Url(64, random);
    challenge = base64url.encode(
      new Uint8Array(await crypto.subtle.digest("SHA-256", encoder.encode(codeVerifier))),
    );
    transaction = await sealTransaction(
      {
        version: OIDC_TRANSACTION_VERSION,
        state,
        nonce,
        code_verifier: codeVerifier,
        return_to: returnTo,
        expires_at: nowEpochSeconds + TRANSACTION_LIFETIME_SECONDS,
      },
      environment.AGAS_SESSION_ENCRYPTION_KEY,
    );
  } catch {
    return errorResponse(500, "Unable to start login.");
  }

  const authorization = new URL(config.authorizationUrl);
  authorization.searchParams.set("response_type", "code");
  authorization.searchParams.set("client_id", config.clientId);
  authorization.searchParams.set("redirect_uri", redirectUri(config));
  authorization.searchParams.set("scope", config.scopes.join(" "));
  authorization.searchParams.set("state", state);
  authorization.searchParams.set("nonce", nonce);
  authorization.searchParams.set("code_challenge", challenge);
  authorization.searchParams.set("code_challenge_method", "S256");
  if (config.audience) authorization.searchParams.set("audience", config.audience);
  if (config.resource) authorization.searchParams.set("resource", config.resource);

  return new Response(null, {
    status: 303,
    headers: {
      "Cache-Control": "no-store",
      Location: authorization.toString(),
      "Set-Cookie": secureCookie(
        OIDC_TRANSACTION_COOKIE_NAME,
        transaction,
        TRANSACTION_LIFETIME_SECONDS,
      ),
    },
  });
}

export async function handleOidcCallback(
  request: Request,
  fetcher: typeof fetch = fetch,
  verifyIdToken: VerifyIdToken = verifyOidcIdToken,
  environment: OidcEnvironment = currentEnvironment(),
  nowEpochSeconds = Math.floor(Date.now() / 1_000),
): Promise<Response> {
  let config: OidcConfig;
  let transaction: OidcTransaction | null;
  try {
    config = oidcConfig(environment);
    transaction = await readTransaction(
      request.headers.get("cookie"),
      environment.AGAS_SESSION_ENCRYPTION_KEY,
      nowEpochSeconds,
    );
  } catch (error) {
    if (error instanceof OidcConfigurationError || error instanceof SessionConfigurationError) {
      return errorResponse(503, "Login service is unavailable.", true);
    }
    return errorResponse(500, "Unable to complete login.", true);
  }
  if (transaction === null) {
    return errorResponse(400, "Login transaction is missing or expired.", true);
  }

  const requestUrl = new URL(request.url);
  if (requestUrl.searchParams.has("error")) {
    return errorResponse(400, "Identity provider did not complete login.", true);
  }
  const codes = requestUrl.searchParams.getAll("code");
  const states = requestUrl.searchParams.getAll("state");
  if (
    codes.length !== 1 ||
    states.length !== 1 ||
    !(codes[0] ?? "").trim() ||
    (codes[0] ?? "").length > 2_048 ||
    (states[0] ?? "").length > 512 ||
    !safeEqual(states[0] ?? "", transaction.state)
  ) {
    return errorResponse(400, "Login callback is invalid.", true);
  }

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code: codes[0]!,
    redirect_uri: redirectUri(config),
    code_verifier: transaction.code_verifier,
  });
  if (config.resource) body.set("resource", config.resource);

  let providerResponse: Response;
  try {
    providerResponse = await fetcher(config.tokenUrl, {
      method: "POST",
      headers: {
        Accept: "application/json",
        Authorization: clientAuthorization(config),
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body,
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(TOKEN_TIMEOUT_MS),
    });
  } catch {
    return errorResponse(502, "Identity provider is unavailable.", true);
  }
  if (
    !providerResponse.ok ||
    !providerResponse.headers.get("content-type")?.includes("application/json")
  ) {
    return errorResponse(502, "Identity provider returned an invalid response.", true);
  }

  let responseText: string | null;
  try {
    responseText = await boundedText(providerResponse);
  } catch {
    return errorResponse(502, "Identity provider returned an invalid response.", true);
  }
  let tokens: ReturnType<typeof tokenResponse> = null;
  if (responseText !== null) {
    try {
      tokens = tokenResponse(JSON.parse(responseText) as unknown);
    } catch {
      tokens = null;
    }
  }
  if (tokens === null) {
    return errorResponse(502, "Identity provider returned an invalid response.", true);
  }

  try {
    await verifyIdToken(tokens.idToken, config, transaction.nonce, nowEpochSeconds);
  } catch {
    return errorResponse(502, "Identity provider returned an invalid identity token.", true);
  }

  const lifetime = Math.min(tokens.expiresIn, MAX_SESSION_SECONDS);
  let session: string;
  try {
    session = await sealServerSession(
      tokens.accessToken,
      nowEpochSeconds + lifetime,
      environment.AGAS_SESSION_ENCRYPTION_KEY,
      nowEpochSeconds,
    );
  } catch {
    return errorResponse(500, "Unable to create browser session.", true);
  }
  const headers = new Headers({
    "Cache-Control": "no-store",
    Location: new URL(transaction.return_to, config.publicOrigin).toString(),
  });
  headers.append("Set-Cookie", clearCookie(OIDC_TRANSACTION_COOKIE_NAME));
  headers.append("Set-Cookie", secureCookie(SESSION_COOKIE_NAME, session, lifetime));
  return new Response(null, { status: 303, headers });
}

export function handleOidcLogout(
  request: Request,
  environment: OidcEnvironment = currentEnvironment(),
): Response {
  let publicOrigin: URL;
  try {
    publicOrigin = secureUrl(environment.AGAS_PUBLIC_WEB_ORIGIN, "Public web origin", true);
  } catch {
    return errorResponse(503, "Logout service is unavailable.");
  }
  const origin = request.headers.get("origin");
  const fetchSite = request.headers.get("sec-fetch-site");
  if (origin !== publicOrigin.origin || (fetchSite !== null && fetchSite !== "same-origin")) {
    return errorResponse(403, "Request origin is not allowed.");
  }

  const headers = new Headers({
    "Cache-Control": "no-store",
    Location: publicOrigin.toString(),
  });
  headers.append("Set-Cookie", clearCookie(OIDC_TRANSACTION_COOKIE_NAME));
  headers.append("Set-Cookie", clearCookie(SESSION_COOKIE_NAME));
  return new Response(null, { status: 303, headers });
}
