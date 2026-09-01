import { base64url, CompactEncrypt, compactDecrypt } from "jose";

export const SESSION_COOKIE_NAME = "__Host-agas-session";
export const SESSION_ENVELOPE_VERSION = 1;

const encoder = new TextEncoder();
const decoder = new TextDecoder();

type SessionEnvelope = {
  access_token: string;
  expires_at: number;
  version: typeof SESSION_ENVELOPE_VERSION;
};

export class SessionConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SessionConfigurationError";
  }
}

export function sessionEncryptionKey(encodedKey: string | undefined): Uint8Array {
  const normalized = encodedKey?.trim();
  if (!normalized) {
    throw new SessionConfigurationError("Session encryption is not configured.");
  }
  let decoded: Uint8Array;
  try {
    decoded = base64url.decode(normalized);
  } catch {
    throw new SessionConfigurationError("Session encryption key is not valid base64url.");
  }
  if (decoded.byteLength !== 32) {
    throw new SessionConfigurationError("Session encryption key must decode to exactly 32 bytes.");
  }
  return decoded;
}

function parseEnvelope(value: unknown, nowEpochSeconds: number): SessionEnvelope | null {
  if (typeof value !== "object" || value === null) return null;
  const candidate = value as Partial<SessionEnvelope>;
  if (
    candidate.version !== SESSION_ENVELOPE_VERSION ||
    typeof candidate.access_token !== "string" ||
    !candidate.access_token.trim() ||
    !Number.isInteger(candidate.expires_at) ||
    (candidate.expires_at ?? 0) <= nowEpochSeconds
  ) {
    return null;
  }
  return {
    access_token: candidate.access_token,
    expires_at: candidate.expires_at as number,
    version: SESSION_ENVELOPE_VERSION,
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

export async function sealServerSession(
  accessToken: string,
  expiresAtEpochSeconds: number,
  encodedKey = process.env.AGAS_SESSION_ENCRYPTION_KEY,
  nowEpochSeconds = Math.floor(Date.now() / 1000),
): Promise<string> {
  const envelope = parseEnvelope(
    {
      access_token: accessToken,
      expires_at: expiresAtEpochSeconds,
      version: SESSION_ENVELOPE_VERSION,
    },
    nowEpochSeconds,
  );
  if (envelope === null) throw new Error("A non-empty access token and future expiry are required.");

  return new CompactEncrypt(encoder.encode(JSON.stringify(envelope)))
    .setProtectedHeader({ alg: "dir", enc: "A256GCM", typ: "agas-session+jwe" })
    .encrypt(sessionEncryptionKey(encodedKey));
}

export async function readServerSessionAccessToken(
  cookieHeader: string | null,
  encodedKey = process.env.AGAS_SESSION_ENCRYPTION_KEY,
  nowEpochSeconds = Math.floor(Date.now() / 1000),
): Promise<string | null> {
  const key = sessionEncryptionKey(encodedKey);
  const encrypted = cookieValue(cookieHeader, SESSION_COOKIE_NAME);
  if (encrypted === null) return null;

  try {
    const { plaintext, protectedHeader } = await compactDecrypt(encrypted, key, {
      contentEncryptionAlgorithms: ["A256GCM"],
      keyManagementAlgorithms: ["dir"],
    });
    if (
      protectedHeader.alg !== "dir" ||
      protectedHeader.enc !== "A256GCM" ||
      protectedHeader.typ !== "agas-session+jwe"
    ) {
      return null;
    }
    const envelope = parseEnvelope(JSON.parse(decoder.decode(plaintext)) as unknown, nowEpochSeconds);
    return envelope?.access_token ?? null;
  } catch {
    return null;
  }
}
