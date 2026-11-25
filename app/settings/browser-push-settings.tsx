"use client";

import { useEffect, useState } from "react";
import {
  browserPushAvailable,
  browserPushRegistered,
  enableBrowserPush,
  disableBrowserPush
} from "../../lib/browser-push";

export function BrowserPushSettings() {
  const [available, setAvailable] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    setAvailable(browserPushAvailable());
    setEnabled(browserPushRegistered());
  }, []);

  async function toggle() {
    setBusy(true);
    setNotice("");

    try {
      if (enabled) {
        await disableBrowserPush();
        setEnabled(false);
        setNotice("Browser notifications disabled.");
      } else {
        await enableBrowserPush();
        setEnabled(true);
        setNotice("Browser notifications enabled.");
      }
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Notification settings could not be updated."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="app-card settings-form">
      <h2>Browser notifications</h2>

      <div className="phone-verification">
        <strong>
          {enabled ? "Notifications enabled" : "Stay up to date"}
        </strong>

        <p>
          Receive important handEwork updates on this browser,
          even when you are not viewing the website.
        </p>

        <button
          type="button"
          className="button button-orange"
          disabled={busy || (!available && !enabled)}
          onClick={() => void toggle()}
        >
          {busy
            ? "Updating..."
            : enabled
              ? "Disable browser notifications"
              : "Enable browser notifications"}
        </button>

        {!available && !enabled && (
          <p>Browser notifications are currently unavailable.</p>
        )}

        {notice && <p role="status">{notice}</p>}
      </div>
    </section>
  );
}
