"use client";

import { useState } from "react";
import { api } from "../../lib/api";
import { GoogleButton } from "../components/google-button";

export function GoogleLinkSettings() {
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [notice, setNotice] = useState("");
  async function link(credential: string) {
    setNotice("");
    try {
      const result = await api<{ message: string }>("/v1/auth/google/link", { method: "POST", body: JSON.stringify({ credential, password, totp_code: code }) });
      setPassword(""); setCode(""); setNotice(result.message);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Unable to link this Google account."); }
  }
  return <section className="app-card settings-form"><h2>Google sign-in</h2><p>Connect your Google account to sign in securely. Confirm your current password and, if enabled, an authenticator code.</p>
    <label>Current handEwork password<input type="password" value={password} autoComplete="current-password" onChange={event => setPassword(event.target.value)} /></label>
    <label>Authenticator code (if enabled)<input value={code} autoComplete="one-time-code" onChange={event => setCode(event.target.value)} /></label>
    {password && <GoogleButton onCredential={credential => { void link(credential); }} label="continue_with" />}
    {notice && <p role="status">{notice}</p>}
  </section>;
}
