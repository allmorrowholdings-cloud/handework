"use client";
import { useState, type FormEvent } from "react";
import { useHydrated } from "../../../components/use-hydrated";
import { api } from "../../../../lib/api";

export function AccountEmailForm({ action }: { action: "verify" | "reset" }) {
  const hydrated = useHydrated();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>, operation: "request" | "confirm") {
    event.preventDefault();
    const form = event.currentTarget;
    setBusy(true);
    try {
      const fields = Object.fromEntries(new FormData(form));
      const result = await api<{message: string}>(`/v1/auth/email/${action}/${operation}`, {
        method: "POST", body: JSON.stringify({ ...fields, email })
      });
      setMessage(result.message);
      if (operation === "confirm") form.reset();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  return <>
    <form method="post" className="action-form" onSubmit={event => submit(event, "request")}>
      <label>Email address<input type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)}/></label>
      <button className="button" disabled={!hydrated || busy}>Send a code</button>
    </form>
    <form method="post" className="action-form" onSubmit={event => submit(event, "confirm")}>
      <label>Code from your email<input name="code" required autoComplete="one-time-code" maxLength={16}/></label>
      {action === "reset" && <label>New password<input type="password" name="password" autoComplete="new-password" required minLength={8}/></label>}
      <button className="button" disabled={!hydrated || busy || !email}>{action === "reset" ? "Reset password" : "Verify email"}</button>
    </form>
    <p role="status">{message}</p>
  </>;
}
