"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api, dashboardPath, saveSession } from "../../lib/api";

type Session = { access_token: string; refresh_token?: string; user: { role: string } };

export function AuthForm({ mode, onAuthenticated, onSwitch }: { mode: "sign-in" | "create"; onAuthenticated?: () => void; onSwitch?: () => void }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const session = await api<Session>(mode === "sign-in" ? "/v1/auth/login" : "/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({ ...data, client: "web" }),
      });
      saveSession(session.access_token, session.refresh_token);
      if (onAuthenticated) onAuthenticated();
      else router.replace(dashboardPath(session.user.role));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not continue");
    } finally {
      setBusy(false);
    }
  }

  return <form className="auth-form" onSubmit={submit}>
    {mode === "create" && <div className="two-fields"><label>First name<input required name="first_name" autoComplete="given-name" /></label><label>Last name<input required name="last_name" autoComplete="family-name" /></label></div>}
    <label>Email address<input required type="email" name="email" autoComplete="email" /></label>
    {mode === "create" && <label>Mobile number<input required type="tel" name="phone" autoComplete="tel" placeholder="+233" /></label>}
    <label>Password
      <span className="password-field">
        <input required minLength={8} type={showPassword ? "text" : "password"} name="password" autoComplete={mode === "sign-in" ? "current-password" : "new-password"} />
        <button type="button" className="password-toggle" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? "Hide" : "Show"}</button>
      </span>
    </label>
    {mode === "create" && <input type="hidden" name="role" value="customer" />}
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="button button-orange full-button" disabled={busy}>{busy ? "Please wait…" : mode === "sign-in" ? "Sign in securely" : "Create customer account"}</button>
    <p className="auth-switch">{onSwitch ? <button type="button" className="text-link" onClick={onSwitch}>{mode === "sign-in" ? "Create an account" : "Sign in instead"}</button> : mode === "sign-in" ? <>New to handEwork? <Link href="/auth/create-account">Create an account</Link></> : <>Already registered? <Link href="/auth/sign-in">Sign in</Link></>}</p>
  </form>;
}
