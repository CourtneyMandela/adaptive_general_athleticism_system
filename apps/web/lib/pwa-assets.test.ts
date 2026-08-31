import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const publicDirectory = join(process.cwd(), "public");
const appDirectory = join(process.cwd(), "app");

describe("PWA shell assets", () => {
  it("declares standalone, ordinary, and maskable install metadata", () => {
    const manifest = JSON.parse(
      readFileSync(join(publicDirectory, "manifest.webmanifest"), "utf8"),
    ) as {
      display: string;
      id: string;
      icons: { purpose: string; src: string; type: string }[];
      scope: string;
      start_url: string;
    };

    expect(manifest).toMatchObject({
      display: "standalone",
      id: "/",
      scope: "/",
      start_url: "/",
    });
    expect(manifest.icons).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          purpose: "any",
          src: "/icons/agas-icon.svg",
          type: "image/svg+xml",
        }),
        expect.objectContaining({
          purpose: "maskable",
          src: "/icons/agas-icon-maskable.svg",
          type: "image/svg+xml",
        }),
      ]),
    );
  });

  it("caches only shell assets and never implements an athlete-data outbox", () => {
    const serviceWorker = readFileSync(join(publicDirectory, "sw.js"), "utf8");
    const offlinePage = readFileSync(join(publicDirectory, "offline.html"), "utf8");
    const registration = readFileSync(join(appDirectory, "pwa-service-worker.tsx"), "utf8");

    expect(serviceWorker).toContain('request.mode === "navigate"');
    expect(serviceWorker).toContain('caches.match("/offline.html")');
    expect(serviceWorker).toContain('url.pathname.startsWith("/_next/static/")');
    expect(serviceWorker).toContain('name.startsWith("agas-shell-")');
    expect(serviceWorker).not.toContain("/v1/");
    expect(serviceWorker).not.toContain("localStorage");
    expect(serviceWorker).not.toContain("indexedDB");
    expect(serviceWorker).not.toContain('addEventListener("sync"');
    expect(offlinePage).toContain("No athlete data is shown, changed, or queued");
    expect(registration).toContain('process.env.NODE_ENV !== "production"');
    expect(registration).toContain('register("/sw.js", { scope: "/" })');
  });
});
