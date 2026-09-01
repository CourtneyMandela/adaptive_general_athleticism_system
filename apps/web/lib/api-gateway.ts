import { SessionConfigurationError, readServerSessionAccessToken } from "./server-session";

const MAX_REQUEST_BYTES = 1_048_576;
const UPSTREAM_TIMEOUT_MS = 15_000;
const BODY_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const ALLOWED_METHODS = new Set(["GET", "HEAD", ...BODY_METHODS]);
const REQUEST_HEADERS = ["accept", "content-type", "idempotency-key", "if-match"];
const RESPONSE_HEADERS = ["content-type", "etag", "retry-after", "x-request-id"];

type GatewayEnvironment = Readonly<{
  AGAS_INTERNAL_API_URL?: string;
  AGAS_INTERNAL_API_HOSTPORT?: string;
  AGAS_PUBLIC_WEB_ORIGIN?: string;
  AGAS_SESSION_ENCRYPTION_KEY?: string;
}>;

function jsonError(status: number, detail: string): Response {
  return Response.json(
    { detail },
    { status, headers: { "Cache-Control": "no-store" } },
  );
}

function configuredOrigin(raw: string | undefined, label: string, requireSecure = false): URL {
  const normalized = raw?.trim();
  if (!normalized) throw new SessionConfigurationError(`${label} is not configured.`);
  let url: URL;
  try {
    url = new URL(normalized);
  } catch {
    throw new SessionConfigurationError(`${label} is invalid.`);
  }
  if (!new Set(["http:", "https:"]).has(url.protocol) || url.username || url.password) {
    throw new SessionConfigurationError(`${label} must be an HTTP(S) origin without credentials.`);
  }
  if (url.pathname !== "/" || url.search || url.hash) {
    throw new SessionConfigurationError(`${label} must not contain a path, query, or fragment.`);
  }
  const loopback = new Set(["localhost", "127.0.0.1", "[::1]"]).has(url.hostname);
  if (requireSecure && url.protocol !== "https:" && !loopback) {
    throw new SessionConfigurationError(`${label} must use HTTPS outside local development.`);
  }
  return url;
}

function configuredInternalOrigin(environment: GatewayEnvironment): URL {
  const origin = environment.AGAS_INTERNAL_API_URL?.trim();
  const hostport = environment.AGAS_INTERNAL_API_HOSTPORT?.trim();
  if (origin && hostport) {
    throw new SessionConfigurationError("Internal API configuration is ambiguous.");
  }
  if (origin) return configuredOrigin(origin, "Internal API origin");
  if (!hostport || !/^[a-z0-9.-]+:\d{1,5}$/iu.test(hostport)) {
    throw new SessionConfigurationError("Internal API host and port are not configured.");
  }
  const port = Number(hostport.slice(hostport.lastIndexOf(":") + 1));
  if (!Number.isInteger(port) || port < 1 || port > 65_535) {
    throw new SessionConfigurationError("Internal API host and port are invalid.");
  }
  return configuredOrigin(`http://${hostport}`, "Internal API origin");
}

function requestIsSameOriginWrite(request: Request, publicOrigin: URL): boolean {
  const origin = request.headers.get("origin");
  if (origin !== publicOrigin.origin) return false;
  const fetchSite = request.headers.get("sec-fetch-site");
  return fetchSite === null || fetchSite === "same-origin";
}

function forwardedRequestHeaders(request: Request, accessToken: string): Headers {
  const headers = new Headers({ Authorization: `Bearer ${accessToken}` });
  for (const name of REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value !== null) headers.set(name, value);
  }
  return headers;
}

async function requestBody(request: Request): Promise<ArrayBuffer | undefined | "too-large"> {
  if (!BODY_METHODS.has(request.method)) return undefined;
  const declaredLength = request.headers.get("content-length");
  if (declaredLength !== null) {
    const parsedLength = Number(declaredLength);
    if (!Number.isFinite(parsedLength) || parsedLength < 0 || parsedLength > MAX_REQUEST_BYTES) {
      return "too-large";
    }
  }
  if (request.body === null) return new ArrayBuffer(0);

  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let totalBytes = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    totalBytes += value.byteLength;
    if (totalBytes > MAX_REQUEST_BYTES) {
      await reader.cancel();
      return "too-large";
    }
    chunks.push(value);
  }

  const body = new Uint8Array(totalBytes);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return body.buffer;
}

function upstreamUrl(internalOrigin: URL, segments: readonly string[], requestUrl: URL): URL {
  const target = new URL(internalOrigin.origin);
  target.pathname = `/${segments.map((segment) => encodeURIComponent(segment)).join("/")}`;
  target.search = requestUrl.search;
  return target;
}

export async function handleApiGateway(
  request: Request,
  segments: readonly string[],
  fetcher: typeof fetch = fetch,
  environment: GatewayEnvironment = {
    AGAS_INTERNAL_API_URL: process.env.AGAS_INTERNAL_API_URL,
    AGAS_INTERNAL_API_HOSTPORT: process.env.AGAS_INTERNAL_API_HOSTPORT,
    AGAS_PUBLIC_WEB_ORIGIN: process.env.AGAS_PUBLIC_WEB_ORIGIN,
    AGAS_SESSION_ENCRYPTION_KEY: process.env.AGAS_SESSION_ENCRYPTION_KEY,
  },
): Promise<Response> {
  if (!ALLOWED_METHODS.has(request.method)) {
    return jsonError(405, "Method not allowed.");
  }
  if (
    segments.length === 0 ||
    segments.some((segment) => !segment || segment === "." || segment === "..")
  ) {
    return jsonError(404, "API route not found.");
  }

  let internalOrigin: URL;
  let publicOrigin: URL;
  let accessToken: string | null;
  try {
    internalOrigin = configuredInternalOrigin(environment);
    publicOrigin = configuredOrigin(
      environment.AGAS_PUBLIC_WEB_ORIGIN,
      "Public web origin",
      true,
    );
    accessToken = await readServerSessionAccessToken(
      request.headers.get("cookie"),
      environment.AGAS_SESSION_ENCRYPTION_KEY,
    );
  } catch (error) {
    if (error instanceof SessionConfigurationError) {
      return jsonError(503, "Browser session service is unavailable.");
    }
    return jsonError(500, "Unable to process browser session.");
  }
  if (accessToken === null) return jsonError(401, "Authentication is required.");
  if (BODY_METHODS.has(request.method) && !requestIsSameOriginWrite(request, publicOrigin)) {
    return jsonError(403, "Request origin is not allowed.");
  }

  const body = await requestBody(request);
  if (body === "too-large") return jsonError(413, "Request body is too large.");

  const target = upstreamUrl(internalOrigin, segments, new URL(request.url));
  let upstream: Response;
  try {
    upstream = await fetcher(target, {
      method: request.method,
      headers: forwardedRequestHeaders(request, accessToken),
      body,
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
    });
  } catch {
    return jsonError(502, "Athlete data service is unavailable.");
  }

  const headers = new Headers({ "Cache-Control": "no-store" });
  for (const name of RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value !== null) headers.set(name, value);
  }
  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers,
  });
}
