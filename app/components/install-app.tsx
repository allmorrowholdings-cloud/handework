"use client";

import { useEffect, useState } from "react";

type InstallPrompt = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{
    outcome: "accepted" | "dismissed";
  }>;
};

export function InstallApp() {
  const [promptEvent, setPromptEvent] =
    useState<InstallPrompt | null>(null);

  const [ios, setIos] = useState(false);
  const [installed, setInstalled] = useState(false);
  const [instructions, setInstructions] = useState(false);

  useEffect(() => {
    const standalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      (
        "standalone" in navigator &&
        (navigator as Navigator & {
          standalone?: boolean
        }).standalone === true
      );

    setInstalled(standalone);
    setIos(/iPad|iPhone|iPod/i.test(navigator.userAgent));

    function available(event: Event) {
      event.preventDefault();
      setPromptEvent(event as InstallPrompt);
    }

    function onInstalled() {
      setInstalled(true);
      setPromptEvent(null);
    }

    window.addEventListener("beforeinstallprompt", available);
    window.addEventListener("appinstalled", onInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", available);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  async function install() {
    if (promptEvent) {
      await promptEvent.prompt();
      await promptEvent.userChoice;
      setPromptEvent(null);
    } else {
      setInstructions(value => !value);
    }
  }

  if (installed || (!promptEvent && !ios)) {
    return null;
  }

  return (
    <div className="footer-install">
      <div>
        <strong>Take handEwork with you.</strong>
        <p>Bookings, messages and WorkProof, one tap away.</p>
      </div>

      <button
        type="button"
        onClick={() => void install()}
      >
        Install handEwork
      </button>

      {instructions && ios && (
        <p className="footer-install-help" role="status">
          In Safari, tap Share, then Add to Home Screen.
        </p>
      )}
    </div>
  );
}
