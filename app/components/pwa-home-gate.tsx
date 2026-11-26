"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { accessToken, api, dashboardPath } from "../../lib/api";

export function PwaHomeGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<"checking" | "public">("checking");

  useEffect(() => {
    let alive = true;
    const standalone = window.matchMedia("(display-mode: standalone)").matches ||
      ("standalone" in navigator && (navigator as Navigator & { standalone?: boolean }).standalone === true);
    if (!standalone || !accessToken()) {
      setState("public");
      return () => { alive = false; };
    }
    api<{ user: { role: string } }>("/v1/auth/me")
      .then(({ user }) => {
        if (!alive) return;
        if (["customer", "artisan", "admin"].includes(user.role)) {
          router.replace(dashboardPath(user.role));
        } else {
          setState("public");
        }
      })
      .catch(() => { if (alive) router.replace("/auth/sign-in"); });
    return () => { alive = false; };
  }, [router]);

  if (state === "checking") {
    return <div className="hw-pwa-checking" role="status" aria-label="Opening handEwork">
      <img src="/app-welcome-logo.svg" alt="handEwork" width={420} height={140} />
    </div>;
  }
  return <>{children}</>;
}
