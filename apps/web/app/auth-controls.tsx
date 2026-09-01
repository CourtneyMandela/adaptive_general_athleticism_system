import { headers } from "next/headers";

import { browserAuthMode } from "@/lib/identity";
import { readServerSessionAccessToken } from "@/lib/server-session";

export async function AuthControls() {
  if (browserAuthMode !== "session") return null;

  let authenticated = false;
  try {
    const requestHeaders = await headers();
    authenticated = Boolean(
      await readServerSessionAccessToken(requestHeaders.get("cookie")),
    );
  } catch {
    authenticated = false;
  }

  return (
    <nav className="auth-controls" aria-label="Account session">
      {authenticated ? (
        <form action="/auth/logout" method="post">
          <span>Secure session active</span>
          <button type="submit" className="text-button">
            Sign out
          </button>
        </form>
      ) : (
        <a href="/auth/login">Sign in securely</a>
      )}
    </nav>
  );
}
