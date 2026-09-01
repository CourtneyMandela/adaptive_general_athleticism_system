import { handleOidcLogout } from "@/lib/oidc-login";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export function POST(request: Request): Response {
  return handleOidcLogout(request);
}
