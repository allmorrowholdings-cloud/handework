"use client";

import { useEffect, useState } from "react";

type InstallPrompt = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};
type Platform = "ios" | "android" | "desktop";

function platform(): Platform {
  const ua = navigator.userAgent;
  if (/iPhone|iPad|iPod/i.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)) return "ios";
  if (/Android/i.test(ua)) return "android";
  return "desktop";
}

export function InstallApp({ compact = false }: { compact?: boolean }) {
  const [promptEvent, setPromptEvent] = useState<InstallPrompt | null>(null);
  const [device, setDevice] = useState<Platform>("desktop");
  const [browser, setBrowser] = useState("Browser");
  const [installed, setInstalled] = useState(false);
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    const standalone = window.matchMedia("(display-mode: standalone)").matches ||
      ("standalone" in navigator && (navigator as Navigator & { standalone?: boolean }).standalone === true);
    setInstalled(standalone);
    setDevice(platform());
    const ua = navigator.userAgent;
    setBrowser(/SamsungBrowser/i.test(ua) ? "Samsung Internet" : /EdgA|EdgiOS|Edg\//i.test(ua) ? "Edge" : /CriOS|Chrome/i.test(ua) ? "Chrome" : /FxiOS|Firefox/i.test(ua) ? "Firefox" : /Safari/i.test(ua) ? "Safari" : "Browser");
    function available(event: Event) { event.preventDefault(); setPromptEvent(event as InstallPrompt); }
    function onInstalled() { setInstalled(true); setPromptEvent(null); setShowHelp(false); }
    window.addEventListener("beforeinstallprompt", available);
    window.addEventListener("appinstalled", onInstalled);
    return () => { window.removeEventListener("beforeinstallprompt", available); window.removeEventListener("appinstalled", onInstalled); };
  }, []);

  async function install() {
    if (promptEvent) {
      try {
        await promptEvent.prompt();
        const choice = await promptEvent.userChoice;
        setPromptEvent(null);
        if (choice.outcome !== "accepted") setShowHelp(true);
      } catch { setShowHelp(true); }
    } else setShowHelp(value => !value);
  }

  if (installed) return null;
  return (
    <div className={compact ? "header-install" : "footer-install"}>
      {!compact && <div><strong>Take handEwork with you.</strong><p>Bookings, messages and WorkProof, one tap away.</p></div>}
      <button type="button" aria-expanded={showHelp} aria-label="Install handEwork or show installation instructions" onClick={() => void install()}>
        {compact ? <><span aria-hidden="true">↓</span><span className="header-install-label">Install app</span></> : "Install handEwork"}
      </button>
      {showHelp && <div className={compact ? "header-install-help" : "footer-install-help"} role="status">
        <button className="install-help-close" type="button" aria-label="Close installation instructions" onClick={() => setShowHelp(false)}>×</button>
        <strong>Install handEwork</strong>
        {device === "ios" ? <p>On iPhone or iPad, open this page in Safari, tap <b>Share</b> (the square with an up arrow), then choose <b>Add to Home Screen</b> and tap <b>Add</b>. If you are using another browser, open this page in Safari first.</p> :
          device === "android" ? <p>On Android, open the browser menu (<b>⋮</b> or <b>☰</b>), choose <b>Install app</b> or <b>Add to Home screen</b>, then confirm. On Samsung Internet, look for <b>Add page to</b> → <b>Home screen</b>. Menu wording varies by browser.</p> :
            <p>On desktop {browser}, look for the install icon in the address bar, or open the browser menu and choose <b>Install handEwork</b>, <b>Install app</b>, or <b>Create shortcut</b>. Options vary by browser.</p>}
        <p className="install-help-hint">If no install option appears, you can still use handEwork normally in your browser.</p>
      </div>}
    </div>
  );
}
