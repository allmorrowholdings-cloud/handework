"use client";

import { useEffect } from "react";
import { accessToken, recordActivity, renewSession } from "../../lib/api";

export function SessionActivity() {
  useEffect(() => {
    let lastTouch = 0;
    let lastRenew = 0;
    function activity() {
      const now = Date.now();
      if (now - lastTouch < 1000) return;
      lastTouch = now;
      recordActivity();
      if (accessToken() && now - lastRenew > 60000) {
        lastRenew = now;
        void renewSession().catch(() => { lastRenew = 0; });
      }
    }
    function checkExpiry() { if (!accessToken()) recordActivity(); }
    activity();
    const timer = window.setInterval(checkExpiry, 30000);
    const events = ["pointerdown", "keydown", "scroll", "focus"];
    for (const event of events) window.addEventListener(event, activity, { passive: true });
    return () => {
      clearInterval(timer);
      for (const event of events) window.removeEventListener(event, activity);
    };
  }, []);
  return null;
}
