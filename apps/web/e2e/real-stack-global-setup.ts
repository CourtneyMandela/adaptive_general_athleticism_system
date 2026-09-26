import { execFileSync, spawn, type ChildProcess } from "node:child_process";
import { once } from "node:events";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

import {
  mockOidcClientId,
  mockOidcClientSecret,
  mockOidcIssuer,
  startMockServices,
} from "./mock-services";

const webOrigin = "http://127.0.0.1:3101";
const apiOrigin = "http://127.0.0.1:3999";
const sessionEncryptionKey = "KSkpKSkpKSkpKSkpKSkpKSkpKSkpKSkpKSkpKSkpKSk";

function requireTestDatabaseUrl(): string {
  const databaseUrl = process.env.AGAS_TEST_DATABASE_URL?.trim();
  if (!databaseUrl) {
    throw new Error(
      "AGAS_TEST_DATABASE_URL is required for the real-stack browser smoke test.",
    );
  }
  const parsed = new URL(databaseUrl);
  if (!parsed.protocol.startsWith("postgresql+") && parsed.protocol !== "postgresql:") {
    throw new Error("AGAS_TEST_DATABASE_URL must use PostgreSQL.");
  }
  if (!parsed.pathname.slice(1).toLocaleLowerCase().endsWith("_test")) {
    throw new Error("AGAS_TEST_DATABASE_URL must target a database ending in _test.");
  }
  return databaseUrl;
}

function pythonExecutable(projectRoot: string): string {
  const configured = process.env.AGAS_E2E_PYTHON?.trim();
  if (configured) return configured;
  const workspacePython = resolve(
    projectRoot,
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
  return existsSync(workspacePython) ? workspacePython : "python";
}

function runPython(
  python: string,
  args: string[],
  projectRoot: string,
  environment: NodeJS.ProcessEnv,
): void {
  execFileSync(python, args, {
    cwd: projectRoot,
    env: environment,
    stdio: "inherit",
    windowsHide: true,
  });
}

async function waitUntilReady(
  child: ChildProcess,
  url: string,
  serviceName: string,
): Promise<void> {
  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`${serviceName} exited with code ${child.exitCode}.`);
    }
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // The service is still starting.
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 250));
  }
  throw new Error(`${serviceName} did not become ready within 120 seconds.`);
}

async function stopProcessTree(child: ChildProcess): Promise<void> {
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
  await Promise.race([
    once(child, "exit"),
    new Promise((resolveDelay) => setTimeout(resolveDelay, 5_000)),
  ]);
  if (child.exitCode === null) child.kill("SIGKILL");
}

export default async function globalSetup() {
  const webRoot = process.cwd();
  const projectRoot = resolve(webRoot, "../..");
  const databaseUrl = requireTestDatabaseUrl();
  const python = pythonExecutable(projectRoot);
  const backendEnvironment = {
    ...process.env,
    AGAS_DATABASE_URL: databaseUrl,
    AGAS_ENVIRONMENT: "test",
    AGAS_AUTH_MODE: "development",
  };
  let migrated = false;
  let api: ChildProcess | undefined;
  let web: ChildProcess | undefined;
  let identity: Awaited<ReturnType<typeof startMockServices>> | undefined;

  try {
    runPython(
      python,
      ["-m", "alembic", "-c", resolve(projectRoot, "alembic.ini"), "upgrade", "head"],
      projectRoot,
      backendEnvironment,
    );
    migrated = true;
    runPython(python, ["-m", "agas_api.seed"], projectRoot, backendEnvironment);

    api = spawn(
      python,
      ["-m", "uvicorn", "agas_api.main:app", "--host", "127.0.0.1", "--port", "3999"],
      {
        cwd: projectRoot,
        env: backendEnvironment,
        stdio: "inherit",
        windowsHide: true,
      },
    );
    await waitUntilReady(api, `${apiOrigin}/ready`, "FastAPI real-stack service");

    identity = await startMockServices({
      includePrivateApi: false,
      redirectUri: `${webOrigin}/auth/callback`,
      resourceOrigin: apiOrigin,
    });
    web = spawn(
      process.execPath,
      ["node_modules/next/dist/bin/next", "dev", "--hostname", "127.0.0.1", "--port", "3101"],
      {
        cwd: webRoot,
        env: {
          ...process.env,
          NEXT_PUBLIC_API_URL: "/api/agas",
          NEXT_PUBLIC_AGAS_AUTH_MODE: "session",
          AGAS_INTERNAL_API_URL: apiOrigin,
          AGAS_PUBLIC_WEB_ORIGIN: webOrigin,
          AGAS_SESSION_ENCRYPTION_KEY: sessionEncryptionKey,
          AGAS_OIDC_ISSUER: mockOidcIssuer,
          AGAS_OIDC_AUTHORIZATION_URL: `${mockOidcIssuer}authorize`,
          AGAS_OIDC_TOKEN_URL: `${mockOidcIssuer}token`,
          AGAS_OIDC_JWKS_URL: `${mockOidcIssuer}jwks`,
          AGAS_OIDC_CLIENT_ID: mockOidcClientId,
          AGAS_OIDC_CLIENT_SECRET: mockOidcClientSecret,
          AGAS_OIDC_SCOPES: "openid agas:api",
          AGAS_OIDC_AUDIENCE: apiOrigin,
          AGAS_OIDC_RESOURCE: apiOrigin,
          AGAS_OIDC_ID_TOKEN_ALGORITHMS: "RS256",
        },
        stdio: "inherit",
        windowsHide: true,
      },
    );
    await waitUntilReady(web, webOrigin, "Next.js real-stack service");
  } catch (error) {
    if (web) await stopProcessTree(web);
    if (identity) await identity.close();
    if (api) await stopProcessTree(api);
    if (migrated) {
      runPython(
        python,
        ["-m", "alembic", "-c", resolve(projectRoot, "alembic.ini"), "downgrade", "base"],
        projectRoot,
        backendEnvironment,
      );
    }
    throw error;
  }

  return async () => {
    if (web) await stopProcessTree(web);
    if (identity) await identity.close();
    if (api) await stopProcessTree(api);
    runPython(
      python,
      ["-m", "alembic", "-c", resolve(projectRoot, "alembic.ini"), "downgrade", "base"],
      projectRoot,
      backendEnvironment,
    );
  };
}
