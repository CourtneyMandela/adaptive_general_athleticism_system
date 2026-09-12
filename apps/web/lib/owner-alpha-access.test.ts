import { describe, expect, it, vi } from "vitest";

import {
  OwnerAlphaAccessError,
  activateOwnerAlphaAccess,
  fetchOwnerAlphaAccess,
  type OwnerAlphaAccessProjection,
} from "./owner-alpha-access";

const projection: OwnerAlphaAccessProjection = {
  access_version: "owner-alpha-operator-access@1.0.0",
  status: "eligible",
  message: "Exact owner may activate.",
  authenticated_issuer: "urn:agas:development",
  authenticated_subject: "local-browser",
  can_activate: true,
  roles: [
    { role: "assessment_reviewer", status: null, assignment_id: null },
    { role: "planning_reviewer", status: null, assignment_id: null },
  ],
};

describe("owner-alpha access client", () => {
  it("loads the projection with the signed-in athlete identity", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(projection), { status: 200 }),
    );

    await expect(fetchOwnerAlphaAccess("http://localhost:8000/", fetcher)).resolves.toEqual(
      projection,
    );
    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/v1/owner-alpha/operator-access",
      { headers: { Accept: "application/json", Authorization: "Bearer dev.local-browser" } },
    );
  });

  it("activates only after the UI attestation", async () => {
    const active = { ...projection, status: "active", can_activate: false } as const;
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ access: active, activated: true }), { status: 200 }),
    );

    await expect(activateOwnerAlphaAccess("/api/agas", fetcher)).resolves.toEqual({
      access: active,
      activated: true,
    });
    expect(fetcher).toHaveBeenCalledWith(
      "/api/agas/v1/owner-alpha/operator-access/activation",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ attestation: true }),
      }),
    );
  });

  it("rejects malformed success bodies and preserves API detail", async () => {
    const malformed = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ status: "eligible" }), { status: 200 }),
    );
    await expect(fetchOwnerAlphaAccess("/api/agas", malformed)).rejects.toEqual(
      new OwnerAlphaAccessError("Operator-access response is invalid.", 200),
    );

    const denied = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Exact identity required." }), { status: 403 }),
    );
    await expect(activateOwnerAlphaAccess("/api/agas", denied)).rejects.toEqual(
      new OwnerAlphaAccessError("Exact identity required.", 403),
    );
  });
});
