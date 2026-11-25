import Link from "next/link";
import { Logo } from "./header";
import { InstallApp } from "./install-app";

export function Footer() {
  return <footer className="site-footer"><div className="shell footer-grid">
    <div><Logo light /><p>Get it done with skilled hands.</p><div className="parent-brand"><img src="/allmorrow-logo.png" alt="ALLMORROW" /><em>Building everything you need next.</em><span>handEwork is an ALLMORROW company.</span></div></div>
    <div><h3>Book</h3><Link href="/marketplace">Find an artisan</Link><Link href="/how-it-works">How it works</Link><Link href="/safety">Safety & trust</Link></div>
    <div><h3>Work</h3><Link href="/join/artisan">Join handEwork</Link><Link href="/artisan/pro">handEwork Pro</Link><Link href="/training">Training</Link></div>
    <div><h3>handEwork</h3><Link href="/about">About</Link><Link href="/support">Support</Link><Link href="/legal/privacy">Privacy</Link><Link href="/legal/terms">Terms</Link></div>
  </div><div className="shell"><InstallApp /></div><div className="shell footer-bottom"><span>Â© 2026 handEwork. Ghana.</span><span>Get it done with skilled hands.</span></div></footer>;
}
