"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { accessToken } from "../../lib/api";
import { useEffect, useState } from "react";
import { ThemeToggle } from "./theme-toggle";

export function Logo({ light = false }: { light?: boolean }) {
  return <Link className={`logo logo-image ${light ? "logo-light" : ""}`} href="/" aria-label="handEwork home">
    <span className="logo-image-wrap"><img className="brand-logo-light" src="/handework-logo.png" alt="handEwork" /><img className="brand-logo-dark" src="/handework-logo-dark.png" alt="" aria-hidden="true" /></span>
  </Link>;
}

export function Header() {
  const [open, setOpen] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  useEffect(() => {
    const sync = () => setSignedIn(Boolean(accessToken()));
    sync();
    window.addEventListener("storage", sync);
    window.addEventListener("handework-session", sync);
    return () => { window.removeEventListener("storage", sync); window.removeEventListener("handework-session", sync); };
  }, []);
  const pathname = usePathname();
  const isHome = pathname === "/";
  return <header className={`site-header ${isHome ? "home-header" : ""}`}><div className="shell nav-wrap">
    <div className="nav-brand"><Logo light={!isHome} /><small>from ALLMORROW</small></div>
    <nav className={open ? "nav-links open" : "nav-links"} aria-label="Main navigation">
      <Link href="/marketplace" onClick={() => setOpen(false)}>Services</Link>
      <Link href="/how-it-works" onClick={() => setOpen(false)}>How it works</Link>
      {signedIn && <Link href="/my-jobs" onClick={() => setOpen(false)}>My jobs</Link>}
      <Link href="/join/artisan" onClick={() => setOpen(false)}>For professionals</Link>
      <div className="mobile-account-links">
        {signedIn ? <>
          <Link href="/my-jobs" onClick={() => setOpen(false)}>My jobs</Link>
          <Link href="/settings" onClick={() => setOpen(false)}>Account & settings</Link>
        </> : (
          <Link href="/auth/sign-in" onClick={() => setOpen(false)}>Sign in</Link>
        )}
        <Link href="/bookings/new" onClick={() => setOpen(false)}>Describe a job</Link>
      </div>
    </nav>
    <div className="nav-actions"><ThemeToggle compact />
      {signedIn && (
        <Link
          className="account-avatar"
          href="/settings"
          aria-label="Account and settings"
          title="Account and settings"
        >
          <svg aria-hidden="true" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round">
            <circle cx="12" cy="8" r="3.5" />
            <path d="M5 20c0-4 3-6 7-6s7 2 7 6" />
          </svg>
        </Link>
      )}<Link className="nav-signin" href={signedIn ? "/my-jobs" : "/auth/sign-in"}>{signedIn ? "Dashboard" : "Sign in"}</Link><Link className="button button-orange nav-cta" href="/bookings/new">Describe a job</Link><button className="menu-button" aria-label="Toggle menu" aria-expanded={open} onClick={() => setOpen(!open)}><span /><span /></button></div>
  </div></header>;
}
