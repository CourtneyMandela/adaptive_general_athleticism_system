import { handleOidcCallback } from "@/lib/oidc-login";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: Request): Promise<Response> {
  return handleOidcCallback(request);
}
