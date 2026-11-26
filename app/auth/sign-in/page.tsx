import Link from "next/link";
import {AppProfessionalLink} from "../../components/app-mode-link";
import { AuthForm } from "../../components/auth-form";
import { Logo } from "../../components/header";
import { ThemeToggle } from "../../components/theme-toggle";
import { AuthSide } from "../../components/auth-side";

export default function SignInPage() { return <main className="auth-page"><section className="auth-panel"><ThemeToggle className="auth-theme" /><Logo /><div className="auth-box"><h1>Continue your work.</h1><p>Sign in to manage bookings, messages and payments.</p><AuthForm mode="sign-in" /><nav className="hw-auth-utility" aria-label="Account help"><Link href="/auth/email/reset">Forgot password?</Link><Link href="/auth/email/verify">Verify email</Link></nav><div className="auth-artisan-cta"><span>Skilled professional?</span><AppProfessionalLink>Work with handEwork</AppProfessionalLink></div></div><div className="auth-footer"><Link className="auth-back" href="/">Back to handEwork</Link><span>from <img src="/allmorrow-logo.png" alt="ALLMORROW" /></span></div></section><AuthSide /></main>; }
