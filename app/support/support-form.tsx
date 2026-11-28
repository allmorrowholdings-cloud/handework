"use client";

import { FormEvent, useState } from "react";
import { api } from "../../lib/api";

export function SupportForm({ initialTopic = "" }: { initialTopic?: string }) {
  const [notice, setNotice] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setNotice("");
    const element = event.currentTarget;
    const form = new FormData(element);
    try { const ticket = await api<{id:string}>("/v1/support", { method:"POST", body:JSON.stringify({ topic:form.get("topic"), email:form.get("email"), message:`From: ${form.get("name")}\n\n${form.get("message")}`, booking_id:form.get("booking_id") || undefined }) }); setNotice(`Request received. Reference ${ticket.id}`); element.reset(); }
    catch (caught) { setNotice(caught instanceof Error ? caught.message : "Support request could not be sent"); }
    finally { setBusy(false); }
  }
  return <form className="app-card support-form" onSubmit={submit}><h2>Send us a message</h2><label>Full name<input name="name" autoComplete="name" required /></label><label>Topic<select name="topic" required defaultValue={initialTopic}><option value="" disabled>Choose a topic</option><option value="general">General enquiry</option><option value="booking">Bookings and job requests</option><option value="payment">Payments and refunds</option><option value="account">Account and verification</option><option value="safety">Safety</option><option value="business">Business</option><option value="partnership">Training and partnerships</option></select></label><label>Email<input required type="email" name="email" /></label><label>Booking reference, if relevant<input name="booking_id" /></label><label>How can we help?<textarea required rows={6} name="message" /></label>{notice && <p className="form-error" role="status">{notice}</p>}<button className="button button-orange hw-contact-submit" disabled={busy}>{busy ? "Sending…" : "Send message"}</button></form>;
}
