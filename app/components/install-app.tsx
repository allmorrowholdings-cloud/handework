"use client";

import { useEffect, useState } from "react";

type InstallPrompt = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};
type Platform = "ios" | "android" | "desktop";

// Only inspect the device when the person chooses Install.
function identifyPlatform(): Platform {
  const ua = navigator.userAgent;
  if (/iPhone|iPad|iPod/i.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)) return "ios";
  if (/Android/i.test(ua)) return "android";
  return "desktop";
}
function identifyBrowser() {
  const ua = navigator.userAgent;
  return /SamsungBrowser/i.test(ua) ? "Samsung Internet" : /EdgA|EdgiOS|Edg\//i.test(ua) ? "Edge" : /CriOS|Chrome/i.test(ua) ? "Chrome" : /FxiOS|Firefox/i.test(ua) ? "Firefox" : /Safari/i.test(ua) ? "Safari" : "Browser";
}
function isInstalled() {
  return window.matchMedia("(display-mode: standalone)").matches ||
    ("standalone" in navigator && (navigator as Navigator & { standalone?: boolean }).standalone === true);
}

export function InstallApp({ compact = false }: { compact?: boolean }) {
  const [promptEvent, setPromptEvent] = useState<InstallPrompt | null>(null);
  const [device, setDevice] = useState<Platform>("desktop");
  const [browser, setBrowser] = useState("Browser");
  const [installed, setInstalled] = useState(false);
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    // This checks install state, not device type. Do not request permissions at install time.
    const frame = window.requestAnimationFrame(() => setInstalled(isInstalled()));
    function available(event: Event) { event.preventDefault(); setPromptEvent(event as InstallPrompt); }
    function onInstalled() { setInstalled(true); setPromptEvent(null); setShowHelp(false); }
    window.addEventListener("beforeinstallprompt", available);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("beforeinstallprompt", available);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  async function install() {
    const detected = identifyPlatform();
    setDevice(detected);
    setBrowser(identifyBrowser());
    if (detected === "ios") { setShowHelp(true); return; }
    if (promptEvent) {
      try {
        await promptEvent.prompt();
        const choice = await promptEvent.userChoice;
        setPromptEvent(null);
        setShowHelp(choice.outcome !== "accepted");
      } catch { setShowHelp(true); }
    } else {
      setShowHelp(true);
    }
  }

  if (installed) return null;
  return <div className={compact ? "header-install" : "footer-install"}>
    {!compact && <div><strong>Take handEwork with you.</strong><p>Bookings, messages and WorkProof, one tap away.</p></div>}
    <button type="button" aria-expanded={showHelp} aria-label="Install handEwork or show installation instructions" onClick={() => void install()}>
      {compact ? <span className="header-install-label">Install app</span> : "Install handEwork"}
    </button>
    {showHelp && <div className={compact ? "header-install-help" : "footer-install-help"} role="status">
      <button className="install-help-close" type="button" aria-label="Close installation instructions" onClick={() => setShowHelp(false)}>×</button>
      <strong>Install handEwork</strong>
      {device === "ios" ? <p>On iPhone or iPad, open handEwork in Safari, tap Share, select Add to Home Screen, then tap Add. Launch handEwork from the new Home Screen icon.</p> :
        device === "android" ? <p>Open your browser menu and select Install app or Add to Home screen. Once installed, open handEwork from your home screen.</p> :
        <p>On desktop {browser}, use your browser&apos;s Install app command in the address bar or browser menu. If not offered, continue using handEwork normally.</p>}

    </div>}
  </div>;
}
