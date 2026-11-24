"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { accessToken, api, dashboardPath, signOut } from "../../lib/api";
import { Logo } from "./header";
import { ThemeToggle } from "./theme-toggle";

const customerLinks = [["/dashboard","Overview"],["/bookings","Bookings"],["/messages","Messages"],["/wallet","Wallet"],["/notifications","Notifications"],["/referrals","Referrals"],["/disputes","Support & disputes"],["/shop","Artisan shop"]];
const artisanLinks = [["/artisan/dashboard","Workboard"],["/artisan/workproof","WorkProof™"],["/artisan/jobs","Jobs"],["/artisan/messages","Messages"],["/artisan/availability","Availability"],["/artisan/portfolio","Portfolio"],["/artisan/earnings","Earnings"],["/artisan/verification","Verification"],["/artisan/pro","handEwork Pro"],["/shop","Artisan shop"]];

export function AppShell({ children, role = "customer", title, note, action }: { children: React.ReactNode; role?: "customer" | "artisan" | "admin"; title: string; note?: string; action?: React.ReactNode }) {
  const path = usePathname(); const router = useRouter();
  const [account, setAccount] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const check = () => {
      if (!accessToken()) { router.replace("/auth/sign-in"); return; }
      api<{user: {role: string}}>("/v1/auth/me", {signal: controller.signal})
        .then(({user}) => {
          if (controller.signal.aborted) return;
          const restricted = path.startsWith("/admin") || path.startsWith("/artisan/") || path === "/dashboard";
          if (restricted && user.role !== role) { router.replace(dashboardPath(user.role)); return; }
          setAccount(user.role);
        }).catch(error => {
          if (controller.signal.aborted) return;
          if (error.status === 401) router.replace("/auth/sign-in");
          else setAccount("error");
        });
    };
    check();
    const changed = () => { if (!accessToken()) router.replace("/auth/sign-in"); };
    window.addEventListener("storage", changed);
    window.addEventListener("handework-session", changed);
    return () => { controller.abort(); window.removeEventListener("storage", changed); window.removeEventListener("handework-session", changed); };
  }, [attempt, path, role, router]);
  if (account === "error") return <p className="section shell" role="status">Your account could not load. <button onClick={() => setAttempt(attempt + 1)}>Try again</button></p>;
  if (!account) return <p className="section shell" role="status">Checking your account...</p>;
  const links = account === "artisan" ? artisanLinks : account === "admin" ? [["/admin","Operations"],["/admin/verifications","KYC queue"],["/admin/disputes","Disputes"],["/admin/payments","Payments"],["/admin/risk","Risk review"],["/admin/analytics","Analytics"]] : customerLinks;
  return <div className="app-layout">
    <aside className="app-sidebar"><Logo light /><nav>{links.map(([href,label]) => <Link className={path === href ? "active" : ""} href={href} key={href}><span>{label.slice(0,1)}</span>{label}</Link>)}</nav><div className="side-bottom"><ThemeToggle /><Link href="/settings">Settings</Link><button onClick={() => { void signOut(); router.push("/auth/sign-in"); }}>Sign out</button></div></aside>
    <div className="app-main"><header className="app-topbar"><div className="mobile-app-logo"><Logo /></div><div><h1>{title}</h1>{note && <p>{note}</p>}</div>{action && <div className="app-action">{action}</div>}</header>{children}</div>
  </div>;
}

export function EmptyState({ mark = "⌁", title, text, action }: { mark?: string; title: string; text: string; action?: React.ReactNode }) {
  return <div className="app-empty"><span>{mark}</span><h2>{title}</h2><p>{text}</p>{action}</div>;
}

export function Stat({ label, value, meta }: { label: string; value: string; meta: string }) {
  return <article className="stat"><span>{label}</span><strong>{value}</strong><small>{meta}</small></article>;
}
