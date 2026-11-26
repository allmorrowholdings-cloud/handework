import Link from "next/link";
import {AppProfessionalLink} from "../../components/app-mode-link";
import { AuthForm } from "../../components/auth-form";
import { Logo } from "../../components/header";
import { ThemeToggle } from "../../components/theme-toggle";
import { AuthSide } from "../../components/auth-side";

export default function CreateAccountPage() { return <main className="auth-page"><section className="auth-panel"><ThemeToggle className="auth-theme" /><Logo /><div className="auth-box"><h1>Create your account.</h1><p>Create a customer account to book and manage skilled work.</p><AuthForm mode="create" /><div className="auth-artisan-cta"><span>Here to earn from your skill?</span><AppProfessionalLink>Work with handEwork</AppProfessionalLink></div></div><div className="auth-footer"><Link className="auth-back" href="/">Back to handEwork</Link><span>from <img src="/allmorrow-logo.png" alt="ALLMORROW" /></span></div></section><AuthSide heading="Your skill. Your proof." /></main>; }
