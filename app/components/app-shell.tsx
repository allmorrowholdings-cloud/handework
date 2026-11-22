"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearSession } from "../../lib/api";
import { Logo } from "./header";
import { ThemeToggle } from "./theme-toggle";

const customerLinks = [["/dashboard","Overview"],["/bookings","Bookings"],["/messages","Messages"],["/wallet","Wallet"],["/notifications","Notifications"],["/referrals","Referrals"],["/disputes","Support & disputes"],["/shop","Artisan shop"]];
const artisanLinks = [["/artisan/dashboard","Workboard"],["/artisan/workproof","WorkProof™"],["/artisan/jobs","Jobs"],["/artisan/messages","Messages"],["/artisan/availability","Availability"],["/artisan/portfolio","Portfolio"],["/artisan/earnings","Earnings"],["/artisan/verification","Verification"],["/artisan/pro","handEwork Pro"],["/shop","Artisan shop"]];

export function AppShell({ children, role = "customer", title, note, action }: { children: React.ReactNode; role?: "customer" | "artisan" | "admin"; title: string; note?: string; action?: React.ReactNode }) {
  const path = usePathname(); const router = useRouter();
  const links = role === "artisan" ? artisanLinks : role === "admin" ? [["/admin","Operations"],["/admin/verifications","KYC queue"],["/admin/disputes","Disputes"],["/admin/payments","Payments"],["/admin/risk","Risk review"],["/admin/analytics","Analytics"]] : customerLinks;
  return <div className="app-layout">
    <aside className="app-sidebar"><Logo light /><nav>{links.map(([href,label]) => <Link className={path === href ? "active" : ""} href={href} key={href}><span>{label.slice(0,1)}</span>{label}</Link>)}</nav><div className="side-bottom"><ThemeToggle /><Link href="/settings">Settings</Link><button onClick={() => { clearSession(); router.push("/auth/sign-in"); }}>Sign out</button></div></aside>
    <div className="app-main"><header className="app-topbar"><div className="mobile-app-logo"><Logo /></div><div><h1>{title}</h1>{note && <p>{note}</p>}</div>{action && <div className="app-action">{action}</div>}</header>{children}</div>
  </div>;
}

export function EmptyState({ mark = "⌁", title, text, action }: { mark?: string; title: string; text: string; action?: React.ReactNode }) {
  return <div className="app-empty"><span>{mark}</span><h2>{title}</h2><p>{text}</p>{action}</div>;
}

export function Stat({ label, value, meta }: { label: string; value: string; meta: string }) {
  return <article className="stat"><span>{label}</span><strong>{value}</strong><small>{meta}</small></article>;
}
