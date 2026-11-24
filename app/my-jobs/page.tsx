"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { accessToken, api, dashboardPath } from "../../lib/api";

export default function MyJobs() {
  const router = useRouter();
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!accessToken()) { router.replace("/auth/sign-in"); return; }
    const controller = new AbortController();
    api<{user: {role: string}}>("/v1/auth/me", { signal: controller.signal })
      .then(({ user }) => { if (!controller.signal.aborted) router.replace(dashboardPath(user.role)); })
      .catch((error) => {
        if (controller.signal.aborted) return;
        if (error.status === 401) router.replace("/auth/sign-in");
        else setError(true);
      });
    return () => controller.abort();
  }, [attempt, router]);
  return <main className="section shell" role="status">{error ? <>Your dashboard could not load. <button onClick={() => { setError(false); setAttempt(attempt + 1); }}>Try again</button></> : "Opening your jobs..."}</main>;
}
