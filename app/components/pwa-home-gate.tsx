"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { accessToken, api, dashboardPath } from "../../lib/api";

function standaloneMode() {
  return window.matchMedia("(display-mode: standalone)").matches ||
    ("standalone" in navigator && (navigator as Navigator & { standalone?: boolean }).standalone === true);
}

export function PwaHomeGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<"checking" | "website" | "pwa-public">("checking");

  useEffect(() => {
    let active = true;
    const standalone = standaloneMode();
    if (standalone && !accessToken()) { router.replace("/app-welcome"); return; }
    const makePublic = (pwa: boolean) => {
      if (!active) return;
      document.documentElement.dataset.pwaPublic = pwa ? "true" : "false";
      // Defer the React update to a browser callback, not the effect body.
      const frame = window.requestAnimationFrame(() => { if (active) setState(pwa ? "pwa-public" : "website"); });
      return frame;
    };
    let frame = 0;
    if (!standalone || !accessToken()) {
      frame = makePublic(standalone) ?? 0;
    } else {
      void api<{ user: { role: string } }>("/v1/auth/me")
        .then(({ user }) => {
          if (!active) return;
          if (["customer", "artisan", "admin"].includes(user.role)) router.replace(dashboardPath(user.role));
          else frame = makePublic(false) ?? 0;
        })
        .catch(() => { if (active) router.replace("/auth/sign-in"); });
    }
    return () => {
      active = false;
      window.cancelAnimationFrame(frame);
      delete document.documentElement.dataset.pwaPublic;
    };
  }, [router]);

  return <>
    <div className={state === "checking" ? "hw-home-checking" : "hw-home-content"}>{children}</div>
    {state === "pwa-public" && <nav className="hw-pwa-quick-nav" aria-label="Quick links">
      <Link href="/marketplace">Services</Link>
      <Link href="/auth/sign-in">Sign in</Link>
      <Link href="/bookings/new">Describe your job</Link>
    </nav>}
  </>;
}
