"use client";

import { useEffect, useSyncExternalStore } from "react";

type Theme = "light" | "dark";

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
}

function subscribe(listener: () => void) {
  window.addEventListener("storage", listener);
  window.addEventListener("handework-theme", listener);
  return () => {
    window.removeEventListener("storage", listener);
    window.removeEventListener("handework-theme", listener);
  };
}

function savedTheme(): Theme {
  const installed = window.matchMedia("(display-mode: standalone)").matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true;
  const value = localStorage.getItem(installed ? "handework_app_theme_v1" : "handework_theme_v2");
  return value === "light" || value === "dark" ? value : "light";
}

export function ThemeInitializer() {
  const theme = useSyncExternalStore(subscribe, savedTheme, () => "light" as const);
  useEffect(() => applyTheme(theme), [theme]);
  return null;
}

export function ThemeToggle({ compact = false, className = "" }: { compact?: boolean; className?: string }) {
  const theme = useSyncExternalStore(subscribe, savedTheme, () => "light" as const);
  useEffect(() => applyTheme(theme), [theme]);

  function toggle() {
    const next: Theme = theme === "light" ? "dark" : "light";
    const installed = window.matchMedia("(display-mode: standalone)").matches ||
      (navigator as Navigator & { standalone?: boolean }).standalone === true;
    window.localStorage.setItem(installed ? "handework_app_theme_v1" : "handework_theme_v2", next);
    window.dispatchEvent(new Event("handework-theme"));
  }

  return (
    <button
      type="button"
      className={`theme-toggle ${compact ? "compact" : ""} ${className}`.trim()}
      onClick={toggle}
      aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
      title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
    >
      <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        {theme === "light"
          ? <path d="M20.5 14.3A8.6 8.6 0 0 1 9.7 3.5a8.8 8.8 0 1 0 10.8 10.8Z" />
          : <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>}
      </svg>
      {!compact && <small>{theme === "light" ? "Dark" : "Light"}</small>}
    </button>
  );
}
