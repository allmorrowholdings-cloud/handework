"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { accessToken, api, dashboardPath } from "../../lib/api";

function installedApp() {
  return window.matchMedia("(display-mode: standalone)").matches ||
    ("standalone" in navigator && (navigator as Navigator & { standalone?: boolean }).standalone === true);
}

export function AppWelcomeClient() {
  const router = useRouter();
  useEffect(() => {
    let active = true;
    const started = Date.now();
    async function continueToApp() {
      let destination = "/";
      if (installedApp() && accessToken()) {
        try {
          const result = await api<{ user: { role: string } }>("/v1/auth/me");
          if (["customer", "artisan", "admin"].includes(result.user.role)) {
            destination = dashboardPath(result.user.role);
          }
        } catch {
          // A stale token or network error must not send someone to an unauthorized dashboard.
          destination = "/auth/sign-in";
        }
      }
      const remaining = Math.max(0, 1100 - (Date.now() - started));
      window.setTimeout(() => { if (active) router.replace(destination); }, remaining);
    }
    void continueToApp();
    return () => { active = false; };
  }, [router]);

  return <main className="hw-pwa-welcome" aria-label="handEwork welcome screen">
    <img src="/app-welcome-logo.svg" alt="handEwork" width={680} height={227} />
    <span className="hw-pwa-welcome-subline">from ALLMORROW</span>
    <span className="hw-pwa-welcome-progress" role="status" aria-label="Opening handEwork" />
  </main>;
}
