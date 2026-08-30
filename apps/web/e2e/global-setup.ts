import { execFileSync, spawn, type ChildProcess } from "node:child_process";

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
  const server = spawn(
    process.execPath,
    ["node_modules/next/dist/bin/next", "dev", "--hostname", "127.0.0.1", "--port", "3100"],
    {
      cwd: process.cwd(),
      env: process.env,
      stdio: "inherit",
      windowsHide: true,
    },
  );
  try {
    await waitUntilReady(server);
  } catch (error) {
    stopProcessTree(server);
    throw error;
  }

  return () => {
    stopProcessTree(server);
  };
}
