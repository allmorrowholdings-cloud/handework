import Link from "next/link";
import { AuthForm } from "../../components/auth-form";
import { Logo } from "../../components/header";
import { ThemeToggle } from "../../components/theme-toggle";

export default function SignInPage() { return <main className="auth-page"><section className="auth-panel"><ThemeToggle className="auth-theme" /><Logo /><div className="auth-box"><h1>Continue your work.</h1><p>Sign in to manage bookings, messages and payments.</p><AuthForm mode="sign-in" /><div className="auth-artisan-cta"><span>Skilled professional?</span><Link href="/join/artisan">Work with handEwork →</Link></div></div><div className="auth-footer"><Link className="auth-back" href="/">← Back to handEwork</Link><span>from <img src="/allmorrow-logo.png" alt="ALLMORROW" /></span></div></section><aside className="auth-art"><div className="auth-word">Skill</div><div><span>One account</span><h2>Every job.<br />Clearly recorded.</h2></div></aside></main>; }
