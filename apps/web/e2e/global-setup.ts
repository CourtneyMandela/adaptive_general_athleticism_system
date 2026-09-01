import { execFileSync, spawn, type ChildProcess } from "node:child_process";

import {
  mockOidcClientId,
  mockOidcClientSecret,
  mockOidcIssuer,
  startMockServices,
} from "./mock-services";

const baseUrl = "http://127.0.0.1:3100";

async function waitUntilReady(child: ChildProcess): Promise<void> {
  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`Next.js smoke-test server exited with code ${child.exitCode}.`);
    }
    try {
      const response = await fetch(baseUrl);
      if (response.ok) return;
    } catch {
      // The server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("Next.js smoke-test server did not become ready within 120 seconds.");
}

function stopProcessTree(child: ChildProcess): void {
  if (child.pid === undefined || child.exitCode !== null) return;
  if (process.platform === "win32") {
    try {
      execFileSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], {
        stdio: "ignore",
        windowsHide: true,
      });
    } catch {
      child.kill();
    }
    return;
  }
  child.kill("SIGTERM");
}

export default async function globalSetup() {
  const mocks = await startMockServices();
  const server = spawn(
    process.execPath,
    ["node_modules/next/dist/bin/next", "dev", "--hostname", "127.0.0.1", "--port", "3100"],
    {
      cwd: process.cwd(),
      env: {
        ...process.env,
        AGAS_INTERNAL_API_URL: "http://127.0.0.1:3999",
        AGAS_PUBLIC_WEB_ORIGIN: baseUrl,
        AGAS_SESSION_ENCRYPTION_KEY: "KSkpKSkpKSkpKSkpKSkpKSkpKSkpKSkpKSkpKSkpKSk",
        AGAS_OIDC_ISSUER: mockOidcIssuer,
        AGAS_OIDC_AUTHORIZATION_URL: `${mockOidcIssuer}authorize`,
        AGAS_OIDC_TOKEN_URL: `${mockOidcIssuer}token`,
        AGAS_OIDC_JWKS_URL: `${mockOidcIssuer}jwks`,
        AGAS_OIDC_CLIENT_ID: mockOidcClientId,
        AGAS_OIDC_CLIENT_SECRET: mockOidcClientSecret,
        AGAS_OIDC_SCOPES: "openid agas:api",
        AGAS_OIDC_RESOURCE: "http://127.0.0.1:3999",
        AGAS_OIDC_ID_TOKEN_ALGORITHMS: "RS256",
      },
      stdio: "inherit",
      windowsHide: true,
    },
  );
  try {
    await waitUntilReady(server);
  } catch (error) {
    stopProcessTree(server);
    await mocks.close();
    throw error;
  }

  return async () => {
    stopProcessTree(server);
    await mocks.close();
  };
}
