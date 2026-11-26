"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { accessToken, api, dashboardPath, signOut } from "../../lib/api";
import { Logo } from "./header";
import { ThemeToggle } from "./theme-toggle";
import {useInstalledApp} from "./installed-app-mode";

const customerLinks = [["/dashboard","Overview"],["/bookings","Bookings"],["/messages","Messages"],["/wallet","Wallet"],["/notifications","Notifications"],["/referrals","Referrals"],["/disputes","Support & disputes"],["/shop","Artisan shop"]];
const artisanLinks = [["/artisan/dashboard","Workboard"],["/artisan/workproof","WorkProof™"],["/artisan/jobs","Jobs"],["/artisan/messages","Messages"],["/artisan/availability","Availability"],["/artisan/portfolio","Portfolio"],["/artisan/earnings","Earnings"],["/artisan/verification","Verification"],["/artisan/pro","handEwork Pro"],["/shop","Artisan shop"],["/training","Training opportunities"]];

export function AppShell({ children, role = "customer", title, note, action }: { children: React.ReactNode; role?: "customer" | "artisan" | "admin"; title: string; note?: string; action?: React.ReactNode }) {
  const path = usePathname(); const router = useRouter(); const installed=useInstalledApp();
  const [appMenu,setAppMenu]=useState<"activities"|"account"|null>(null);
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
  if (!account) return installed ? <div className="hw-app-page-loader" role="status" aria-label="Opening handEwork"><img src="/app-welcome-logo.svg" alt="" width={240} height={80}/></div> : <p className="section shell" role="status">Checking your account...</p>;
  const links = account === "artisan" ? artisanLinks : account === "admin" ? [["/admin","Operations"],["/admin/verifications","KYC queue"],["/admin/disputes","Disputes"],["/admin/payments","Payments"],["/admin/media","Shop media"],["/admin/drive-submissions","Drive link review"],["/admin/risk","Risk review"],["/admin/analytics","Analytics"]] : customerLinks;
  const appCustomer=installed && role==="customer" && account==="customer";
  const activityLinks=[["/app/overview","Overview"],["/bookings","Bookings"],["/messages","Messages"],["/notifications","Notifications"],["/referrals","Referrals"],["/disputes","Support & disputes"]];
  const accountLinks=[["/settings","Settings"],["/wallet","Wallet"],["/support","Help"]];
  if(appCustomer) return <div className="hw-native-app-shell">
    <header className="hw-native-app-top"><span className="hw-app-location">{path==="/dashboard"?"Home":path==="/app/overview"?"Overview":title}</span><Link href="/settings" className="hw-native-avatar" aria-label="Account settings"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.2-7 8-7s8 3 8 7"/></svg></Link></header>
    <main className="hw-native-app-content">{children}</main>
    {appMenu && <div className="hw-app-menu-overlay" onClick={()=>setAppMenu(null)}><nav className="hw-app-menu" aria-label={appMenu==="activities"?"Activities":"Account"} onClick={e=>e.stopPropagation()}><h2>{appMenu==="activities"?"Activities":"Account"}</h2>{(appMenu==="activities"?activityLinks:accountLinks).map(([href,label])=><Link key={href} href={href} onClick={()=>setAppMenu(null)}>{label}</Link>)}{appMenu==="account"&&<button type="button" onClick={()=>{setAppMenu(null);void signOut();router.replace("/auth/sign-in")}}>Sign out</button>}</nav></div>}
    <nav className="hw-app-bottom-nav" aria-label="App navigation"><Link href="/dashboard" aria-current={path==="/dashboard"?"page":undefined} onClick={()=>setAppMenu(null)}><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="m3 10 9-7 9 7v11H3z"/><path d="M9 21v-7h6v7"/></svg><span>Home</span></Link><button type="button" aria-expanded={appMenu==="activities"} onClick={()=>setAppMenu(appMenu==="activities"?null:"activities")}><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg><span>Activities</span></button><button type="button" aria-expanded={appMenu==="account"} onClick={()=>setAppMenu(appMenu==="account"?null:"account")}><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.2-7 8-7s8 3 8 7"/></svg><span>Account</span></button></nav>
  </div>;
  return <div className="app-layout">
    <aside className="app-sidebar"><Logo light /><nav>{links.map(([href,label]) => <Link className={path === href ? "active" : ""} href={href} key={href}><span>{label.slice(0,1)}</span>{label}</Link>)}</nav><div className="side-bottom"><ThemeToggle /><Link href="/submissions">My Drive submissions</Link><Link href="/settings">Settings</Link><button onClick={() => { void signOut(); router.push("/auth/sign-in"); }}>Sign out</button></div></aside>
    <div className="app-main"><header className="app-topbar"><div className="mobile-app-logo"><Logo /></div><div><h1>{title}</h1>{note && <p>{note}</p>}</div>{action && <div className="app-action">{action}</div>}</header>{children}</div>
  </div>;
}

export function EmptyState({ mark = "⌁", title, text, action }: { mark?: string; title: string; text: string; action?: React.ReactNode }) {
  return <div className="app-empty"><span>{mark}</span><h2>{title}</h2><p>{text}</p>{action}</div>;
}

export function Stat({ label, value, meta }: { label: string; value: string; meta: string }) {
  return <article className="stat"><span>{label}</span><strong>{value}</strong><small>{meta}</small></article>;
}
