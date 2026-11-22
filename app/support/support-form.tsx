"use client";

import { FormEvent, useState } from "react";
import { api } from "../../lib/api";

export function SupportForm() {
  const [notice, setNotice] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setNotice("");
    const form = new FormData(event.currentTarget);
    try { const ticket = await api<{id:string}>("/v1/support", { method:"POST", body:JSON.stringify({ topic:form.get("topic"), email:form.get("email"), message:form.get("message"), booking_id:form.get("booking_id") || undefined }) }); setNotice(`Request received. Reference ${ticket.id}`); event.currentTarget.reset(); }
    catch (caught) { setNotice(caught instanceof Error ? caught.message : "Support request could not be sent"); }
    finally { setBusy(false); }
  }
  return <form className="app-card support-form" onSubmit={submit}><h2>Send a support request</h2><label>Topic<select name="topic" required defaultValue=""><option value="" disabled>Choose a topic</option><option value="booking">Booking</option><option value="payment">Payment</option><option value="account">Account</option><option value="safety">Safety</option><option value="business">Business</option><option value="partnership">Partnership</option></select></label><label>Email<input required type="email" name="email" /></label><label>Booking reference, if relevant<input name="booking_id" /></label><label>What happened?<textarea required rows={6} name="message" /></label>{notice && <p className="form-error" role="status">{notice}</p>}<button className="button button-orange" disabled={busy}>{busy ? "Sending…" : "Submit request"}</button></form>;
}
