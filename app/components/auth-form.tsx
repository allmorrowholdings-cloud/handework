"use client";

import Link from "next/link";
import { FormEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, dashboardPath, saveSession } from "../../lib/api";

import { useHydrated } from "./use-hydrated";
import { GoogleButton } from "./google-button";

type Session = { access_token: string; refresh_token?: string; user: { role: string } };

export function AuthForm({ mode, onAuthenticated, onSwitch }: { mode: "sign-in" | "create"; onAuthenticated?: () => void; onSwitch?: () => void }) {
  const ready = useHydrated();
  const router = useRouter();
  const formRef = useRef<HTMLFormElement>(null);
  const [googleCredential, setGoogleCredential] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [secondFactor, setSecondFactor] = useState(false);
  const [recoveryMode, setRecoveryMode] = useState(false);
  const [verificationCode, setVerificationCode] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const session = await api<Session>(googleCredential ? "/v1/auth/google/login" : mode === "sign-in" ? "/v1/auth/login" : "/v1/auth/register", {
        method: "POST",
        body: JSON.stringify(googleCredential ? { credential: googleCredential, totp_code: verificationCode, client: "web" } : { ...data, client: "web" }),
      });
      saveSession(session.access_token, session.refresh_token);
      if (onAuthenticated) onAuthenticated();
      else router.replace(dashboardPath(session.user.role));
    } catch (caught) {
      const details = (
        caught as { details?: { code?: string } }
      )?.details;

      if (mode === "sign-in" && (
        details?.code === "totp_required" ||
        details?.code === "totp_invalid" ||
        details?.code === "totp_locked"
      )) {
        setSecondFactor(true);
      }

      setError(caught instanceof Error ? caught.message : "Could not continue");
    } finally {
      setBusy(false);
    }
  }

  async function signWithGoogle(credential: string) {
    setError(""); setBusy(true);
    try {
      let path = "/v1/auth/google/login";
      let extra: Record<string, string> = {};
      if (mode === "create") {
        path = "/v1/auth/google/register";
        const data = new FormData(formRef.current!);
        extra = Object.fromEntries(["first_name", "last_name", "phone", "password"].map(key => [key, String(data.get(key) ?? "")]));
        if (!extra.first_name || !extra.last_name || !extra.phone || extra.password.length < 12) {
          setError("Enter your name, mobile number and a 12-character password before continuing with Google."); return;
        }
      }
      const session = await api<Session>(path, { method: "POST", body: JSON.stringify({ credential, client: "web", ...extra }) });
      saveSession(session.access_token, session.refresh_token);
      if (onAuthenticated) onAuthenticated();
      else router.replace(dashboardPath(session.user.role));
    } catch (caught) {
      const code = (caught as {details?:{code?:string}})?.details?.code;
      if (code === "totp_required" || code === "totp_invalid") {
        setGoogleCredential(credential); setSecondFactor(true);
      }
      setError(caught instanceof Error ? caught.message : "Google authentication failed");
    } finally { setBusy(false); }
  }

  return <form ref={formRef} noValidate={secondFactor} method="post" className={`auth-form ${secondFactor ? "hw-challenge" : ""}`} onSubmit={submit}>
    <div className="hw-primary-credentials" hidden={secondFactor}>{mode === "create" && <div className="two-fields"><label>First name<input required name="first_name" autoComplete="given-name" /></label><label>Last name<input required name="last_name" autoComplete="family-name" /></label></div>}
    <label>Email address<input required type="email" name="email" autoComplete="email" /></label>
    {mode === "create" && <label>Mobile number<input required type="tel" name="phone" autoComplete="tel" placeholder="+233" /></label>}
    <label>Password
      <span className="password-field">
        <input required minLength={mode === "create" ? 12 : 1} maxLength={mode === "create" ? 128 : undefined} type={showPassword ? "text" : "password"} name="password" autoComplete={mode === "sign-in" ? "current-password" : "new-password"} />
        <button type="button" className="password-toggle" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? "Hide" : "Show"}</button>
      </span>
    </label>
    </div>
    {mode === "sign-in" && secondFactor && (
      <section className="hw-challenge-panel">
        <div className="hw-security-symbol" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6l-8-3Z"/>
            <path d="m9 12 2 2 4-4"/>
          </svg>
        </div>
        <span className="hw-kicker">SECURE ACCESS</span>
        <h2>{recoveryMode ? "Recover your access" : "Verify it's you."}</h2>
        <p>{recoveryMode
          ? "Enter one of your unused emergency recovery codes."
          : "Enter the six-digit code from your authenticator app."}</p>
        <label htmlFor="hw-auth-code">
          {recoveryMode ? "Recovery code" : "Authentication code"}
        </label>
        <input
          id="hw-auth-code"
          className={recoveryMode ? "hw-recovery-input" : "hw-verification-code"}
          required
          name="totp_code"
          type="text"
          value={verificationCode}
          inputMode={recoveryMode ? "text" : "numeric"}
          autoComplete="one-time-code"
          autoCapitalize="none"
          spellCheck={false}
          maxLength={recoveryMode ? 24 : 6}
          pattern={recoveryMode ? undefined : "[0-9]{6}"}
          autoFocus
          placeholder={recoveryMode ? "Recovery code" : "000000"}
          onChange={event => setVerificationCode(
            recoveryMode ? event.target.value
              : event.target.value.replace(/\\D/g, "").slice(0, 6)
          )}
        />
        <button type="button" className="hw-text-button"
          onClick={() => {
            setRecoveryMode(!recoveryMode);
            setVerificationCode("");
            setError("");
          }}>
          {recoveryMode ? "Use authenticator instead" : "Use a recovery code"}
        </button>
        <button type="button" className="hw-text-button"
          onClick={() => {
            setSecondFactor(false);
            setVerificationCode("");
            setRecoveryMode(false);
            setError("");
          }}>
          Back to sign in
        </button>
      </section>
    )}
    {mode === "create" && <input type="hidden" name="role" value="customer" />}
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="button button-orange full-button" disabled={busy || !ready}>{busy ? "Please wait…" : secondFactor ? "Verify and continue" : mode === "sign-in" ? "Sign in securely" : "Create customer account"}</button>
    {mode === "create" && !secondFactor && <p>Choose a unique password or passphrase of 12–128 characters. Enable two-factor authentication in Account security after sign-up.</p>}
    {!secondFactor && <GoogleButton label={mode === "create" ? "signup_with" : "signin_with"} onCredential={credential => { void signWithGoogle(credential); }} />}
    <p className="auth-switch">{onSwitch ? <button type="button" className="text-link" onClick={onSwitch}>{mode === "sign-in" ? "Create an account" : "Sign in instead"}</button> : mode === "sign-in" ? <>New to handEwork? <Link href="/auth/create-account">Create an account</Link></> : <>Already registered? <Link href="/auth/sign-in">Sign in</Link></>}</p>
  </form>;
}
