"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, dashboardPath, saveSession } from "../../lib/api";
import { useHydrated } from "./use-hydrated";
import { GoogleButton } from "./google-button";

function appClient(){if(typeof window==="undefined")return "web";return window.matchMedia("(display-mode: standalone)").matches||((navigator as Navigator & {standalone?:boolean}).standalone===true)?"installed":"web";}

type Session = { access_token: string; refresh_token?: string; user: { role: string } };
type ApiFailure = Error & { details?: { code?: string; profile?: GoogleProfile } };
type GoogleProfile = { first_name?: string; last_name?: string; email?: string };
type Step = "choice" | "profile" | "link" | "mfa" | "complete";
type ChallengeSource = "password" | "google" | "link";

function EyeIcon({ visible }: { visible: boolean }) {
  return <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {visible ? <><path d="M3 3l18 18"/><path d="M10.58 10.59a2 2 0 002.83 2.83"/><path d="M9.88 5.09A10.99 10.99 0 0112 5c5 0 9 4 10 7a12.5 12.5 0 01-2.34 3.61"/><path d="M6.61 6.61C4.4 8.1 2.84 10.07 2 12c1 3 5 7 10 7a10.95 10.95 0 005.39-1.39"/></> : <><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></>}
  </svg>;
}

function CheckMark() {
  return <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m5 12 4.5 4.5L19 7"/></svg>;
}

export function AuthForm({ mode, onAuthenticated, onSwitch }: {
  mode: "sign-in" | "create";
  onAuthenticated?: () => void;
  onSwitch?: () => void;
}) {
  const ready = useHydrated();
  const router = useRouter();
  const [step, setStep] = useState<Step>("choice");
  const [credential, setCredential] = useState("");
  const [profile, setProfile] = useState<GoogleProfile>({});
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [existingPassword, setExistingPassword] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailFirst, setEmailFirst] = useState("");
  const [emailLast, setEmailLast] = useState("");
  const [emailPhone, setEmailPhone] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [recoveryMode, setRecoveryMode] = useState(false);
  const [challengeSource, setChallengeSource] = useState<ChallengeSource>("password");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [destination, setDestination] = useState("/dashboard");

  useEffect(() => {
    if (step !== "complete") return;
    const timer = window.setTimeout(() => {
      if (onAuthenticated) onAuthenticated();
      else router.replace(destination);
    }, 1100);
    return () => window.clearTimeout(timer);
  }, [step, destination, onAuthenticated, router]);

  function complete(session: Session) {
    saveSession(session.access_token, session.refresh_token);
    setCredential("");
    setDestination(dashboardPath(session.user.role));
    setError("");
    setStep("complete");
  }

  function explain(caught: unknown) {
    const failure = caught as ApiFailure;
    setError(failure instanceof Error ? failure.message : "We couldn't complete that step. Try again.");
  }

  async function chooseGoogle(token: string) {
    setError(""); setBusy(true); setCredential(token);
    try {
      const session = await api<Session>("/v1/auth/google/login", {
        method: "POST", body: JSON.stringify({ credential: token, client: appClient() }),
      });
      complete(session);
    } catch (caught) {
      const failure = caught as ApiFailure;
      const code = failure.details?.code;
      if (code === "google_registration_required") {
        const person = failure.details?.profile || {};
        setProfile(person);
        setFirstName(person.first_name || "");
        setLastName(person.last_name || "");
        setStep("profile");
        setError("");
      } else if (code === "google_link_required") {
        setStep("link"); setError("");
      } else if (code === "totp_required") {
        setChallengeSource("google"); setStep("mfa"); setError("");
      } else { explain(caught); }
    } finally { setBusy(false); }
  }

  async function completeGoogleProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setBusy(true);
    try {
      const session = await api<Session>("/v1/auth/google/register", {
        method: "POST",
        body: JSON.stringify({ credential, first_name: firstName.trim(), last_name: lastName.trim(), phone: phone.trim(), password: newPassword, client: appClient() }),
      });
      complete(session);
    } catch (caught) { explain(caught); }
    finally { setBusy(false); }
  }

  async function linkGoogle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setBusy(true);
    try {
      const session = await api<Session>("/v1/auth/google/verify-and-link", {
        method: "POST", body: JSON.stringify({ credential, password: existingPassword, client: appClient() }),
      });
      complete(session);
    } catch (caught) {
      const code = (caught as ApiFailure).details?.code;
      if (code === "totp_required") {
        setStep("mfa"); setChallengeSource("link"); setError("");
      } else explain(caught);
    } finally { setBusy(false); }
  }

  async function submitPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setBusy(true);
    try {
      const session = await api<Session>(mode === "create" ? "/v1/auth/register" : "/v1/auth/login", {
        method: "POST", body: JSON.stringify(mode === "create" ? { email, password, first_name: emailFirst, last_name: emailLast, phone: emailPhone, role: "customer", client: appClient() } : { email, password, client: appClient() }),
      });
      complete(session);
    } catch (caught) {
      const code = (caught as ApiFailure).details?.code;
      if (code === "totp_required") { setChallengeSource("password"); setStep("mfa"); setError(""); }
      else explain(caught);
    } finally { setBusy(false); }
  }

  async function submitMfa(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setBusy(true);
    const endpoint = challengeSource === "google" ? "/v1/auth/google/login"
      : challengeSource === "link" ? "/v1/auth/google/verify-and-link" : "/v1/auth/login";
    const data = challengeSource === "google" ? { credential, totp_code: verificationCode, client: appClient() }
      : challengeSource === "link" ? { credential, password: existingPassword, totp_code: verificationCode, client: appClient() }
      : { email, password, totp_code: verificationCode, client: appClient() };
    try {
      const session = await api<Session>(endpoint, { method: "POST", body: JSON.stringify(data) });
      complete(session);
    } catch (caught) { explain(caught); }
    finally { setBusy(false); }
  }

  function startAgain() {
    setCredential(""); setVerificationCode(""); setRecoveryMode(false);
    setExistingPassword(""); setError(""); setStep("choice");
  }

  if (step === "complete") return <div className="hw-auth-complete" role="status">
    <span className="hw-auth-check"><CheckMark /></span>
    <h2>You&apos;re all set.</h2>
    <p>Your account is ready. Opening your dashboard…</p>
    <button type="button" className="hw-auth-inline-link" onClick={() => {
      if (onAuthenticated) onAuthenticated(); else router.replace(destination);
    }}>Go to dashboard</button>
  </div>;

  if (step === "profile") return <form className="auth-form hw-auth-progress" onSubmit={completeGoogleProfile}>
    <div className="hw-auth-progress-heading"><span className="hw-auth-step">STEP 2 OF 2</span>
      <h2>Hi {firstName || "there"}, finish setting up.</h2>
      <p>Your Google account is connected. Add a few details so you can book and manage work.</p>
      {profile.email && <span className="hw-auth-email">{profile.email}</span>}
    </div>
    <div className="two-fields"><label>First name<input required autoComplete="given-name" maxLength={80} value={firstName} onChange={e => setFirstName(e.target.value)} /></label>
      <label>Last name<input required autoComplete="family-name" maxLength={80} value={lastName} onChange={e => setLastName(e.target.value)} /></label></div>
    <label>Mobile number<input type="tel" required autoComplete="tel" placeholder="+233 24 000 0000" value={phone} onChange={e => setPhone(e.target.value)} /></label>
    <label>Create a password <small>For account recovery and secure settings</small><span className="password-field"><input type={showPassword ? "text" : "password"} minLength={12} maxLength={128} required autoComplete="new-password" value={newPassword} onChange={e => setNewPassword(e.target.value)} /><button type="button" className="password-toggle" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(v => !v)}><EyeIcon visible={showPassword}/></button></span></label>
    <p className="hw-auth-helper">Use 12–128 characters. You can enable an authenticator in Account security.</p>
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="button button-orange full-button" disabled={!ready || busy}>{busy ? "Setting up your account…" : "Complete my account"}</button>
    <button className="hw-auth-inline-link" type="button" onClick={startAgain}>Choose a different Google account</button>
  </form>;

  if (step === "link") return <form className="auth-form hw-auth-progress" onSubmit={linkGoogle}>
    <div className="hw-auth-progress-heading"><span className="hw-auth-step">SECURE ACCOUNT CONNECTION</span>
      <h2>Welcome back.</h2>
      <p>You already have a handEwork account. Enter your existing password once to connect Google. After that, you can use Google to sign in.</p>
    </div>
    <label>Current handEwork password<span className="password-field"><input required autoComplete="current-password" type={showPassword ? "text" : "password"} value={existingPassword} onChange={e => setExistingPassword(e.target.value)} /><button type="button" className="password-toggle" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(v => !v)}><EyeIcon visible={showPassword}/></button></span></label>
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="button button-orange full-button" disabled={!ready || busy}>{busy ? "Connecting securely…" : "Connect Google & continue"}</button>
    <button type="button" className="hw-auth-inline-link" onClick={startAgain}>Back to sign in</button>
  </form>;

  if (step === "mfa") return <form className="auth-form hw-auth-progress" onSubmit={submitMfa}>
    <div className="hw-auth-progress-heading"><span className="hw-auth-step">ACCOUNT PROTECTION</span>
      <h2>One more check.</h2><p>{recoveryMode ? "Use an unused recovery code." : "Enter the six-digit code from your authenticator app."}</p></div>
    <label>{recoveryMode ? "Recovery code" : "Authenticator code"}<input required value={verificationCode} onChange={e => setVerificationCode(recoveryMode ? e.target.value : e.target.value.replace(/\D/g, "").slice(0, 6))} autoComplete="one-time-code" inputMode={recoveryMode ? "text" : "numeric"} autoCapitalize="none" spellCheck={false} maxLength={recoveryMode ? 24 : 6} pattern={recoveryMode ? undefined : "[0-9]{6}"} placeholder={recoveryMode ? "Recovery code" : "000000"} /></label>
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="button button-orange full-button" disabled={!ready || busy}>{busy ? "Verifying…" : "Verify & continue"}</button>
    <button type="button" className="hw-auth-inline-link" onClick={() => { setRecoveryMode(v => !v); setVerificationCode(""); setError(""); }}>{recoveryMode ? "Use authenticator instead" : "Use a recovery code"}</button>
    <button type="button" className="hw-auth-inline-link" onClick={startAgain}>Back to sign in</button>
  </form>;

  return <div className="hw-auth-choice">
    <div className="hw-auth-google-zone">
      <GoogleButton label="continue_with" onCredential={token => { if (!busy) void chooseGoogle(token); }} />
    </div>
    <div className="hw-auth-divider"><span>or continue with email</span></div>
    <form className="auth-form" onSubmit={submitPassword}>
      {mode === "create" && <><div className="two-fields"><label>First name<input required autoComplete="given-name" value={emailFirst} onChange={e => setEmailFirst(e.target.value)}/></label><label>Last name<input required autoComplete="family-name" value={emailLast} onChange={e => setEmailLast(e.target.value)}/></label></div><label>Mobile number<input type="tel" required autoComplete="tel" value={emailPhone} onChange={e => setEmailPhone(e.target.value)} /></label></>}
      <label>Email address<input required type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} /></label>
      <label>Password<span className="password-field"><input required type={showPassword ? "text" : "password"} autoComplete={mode === "create" ? "new-password" : "current-password"} minLength={mode === "create" ? 12 : 1} maxLength={mode === "create" ? 128 : undefined} value={password} onChange={e => setPassword(e.target.value)} /><button type="button" className="password-toggle" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(v => !v)}><EyeIcon visible={showPassword}/></button></span></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="button button-orange full-button" disabled={!ready || busy}>{busy ? "Please wait…" : mode === "create" ? "Create my account" : "Sign in with email"}</button>
    </form>
    {mode === "create" && <p className="hw-auth-helper">New customer? Choose Google above to create an account, or <Link href="/auth/create-account">use the standard signup form</Link>.</p>}
    <p className="auth-switch">{onSwitch ? <button type="button" className="hw-auth-inline-link" onClick={onSwitch}>{mode === "sign-in" ? "Create an account" : "Sign in instead"}</button> : mode === "sign-in" ? <>New to handEwork? <Link href="/auth/create-account">Create an account</Link></> : <>Already registered? <Link href="/auth/sign-in">Sign in</Link></>}</p>
  </div>;
}
