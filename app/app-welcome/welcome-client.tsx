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
    async function continueToApp() {
      let destination = installedApp() ? "/auth/sign-in?app=1" : "/";
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
      if (active) router.replace(destination);
    }
    void continueToApp();
    return () => { active = false; };
  }, [router]);

  return <main className="hw-pwa-welcome" aria-label="handEwork welcome screen">
    <video className="hw-app-splash-video" aria-label="Opening handEwork" src="/handework-opening.mp4" poster="/handework-opening-poster.png" autoPlay muted playsInline preload="auto" />
    <span className="hw-app-splash-brand">from ALLMORROW</span>
  </main>;
}
