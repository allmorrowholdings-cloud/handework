"use client";

import { ChangeEvent, FormEvent, Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppShell } from "../../components/app-shell";
import { api } from "../../../lib/api";

const initial = { service:"", description:"", address:"", area:"", city:"Accra", scheduled_date:"", time_window:"morning", budget_type:"quote", budget:"", contact_phone:"", instant_booking:false };

export default function NewBookingPage() {
  return <Suspense fallback={<p className="shell" role="status">Loading job request…</p>}><NewBookingForm /></Suspense>;
}

function NewBookingForm() {
  const params = useSearchParams();
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({ ...initial, area: params.get("area") ?? "", service: params.get("service") ?? "" });
  const [media, setMedia] = useState<File[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (field:string, value:string|boolean) => setForm((current) => ({ ...current, [field]: value }));
  function files(event: ChangeEvent<HTMLInputElement>) { setMedia(Array.from(event.target.files ?? []).slice(0, 5)); }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    if (step < 3) { setStep(step + 1); return; }
    setBusy(true);
    try {
      const booking = await api<{id:string}>("/v1/bookings", { method:"POST", body:JSON.stringify({ ...form, artisan_id: params.get("artisan") || undefined }) });
      for (const file of media) {
        const upload = new FormData(); upload.append("file", file); upload.append("purpose", "booking_media"); upload.append("booking_id", booking.id);
        await api("/v1/uploads", { method:"POST", body:upload });
      }
      router.push(`/bookings/${booking.id}`);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not create booking"); }
    finally { setBusy(false); }
  }
  return <AppShell title="Request skilled work" note="Nothing is charged until the scope and artisan are confirmed."><section className="app-content narrow-content"><div className="booking-progress"><span className={step>=1?"on":""}>1. Work</span><span className={step>=2?"on":""}>2. Place & time</span><span className={step>=3?"on":""}>3. Budget & review</span></div><form className="app-card booking-form" onSubmit={submit}>
    {step===1 && <><h2>What needs doing?</h2><label>Service category<input required value={form.service} onChange={(event)=>set("service",event.target.value)} placeholder="Plumbing, makeup, carpentry…" /></label><label>Job details<textarea required value={form.description} onChange={(event)=>set("description",event.target.value)} rows={6} placeholder="Describe the problem or result you need. Include measurements or useful details." /></label><label className="upload-zone">Photos or short video<input type="file" multiple accept="image/*,video/*" onChange={files} /><span>{media.length ? `${media.length} file${media.length===1?"":"s"} selected` : "Add up to five clear job photos"}</span></label></>}
    {step===2 && <><h2>Where and when?</h2><label>Job address<input required value={form.address} onChange={(event)=>set("address",event.target.value)} placeholder="House number, street or landmark" /></label><div className="two-fields"><label>Area<input required value={form.area} onChange={(event)=>set("area",event.target.value)} placeholder="e.g. East Legon" /></label><label>City<select value={form.city} onChange={(event)=>set("city",event.target.value)}><option>Accra</option><option>Kumasi</option><option>Tema</option><option>Takoradi</option><option>Cape Coast</option><option>Tamale</option></select></label></div><div className="two-fields"><label>Date<input required type="date" value={form.scheduled_date} onChange={(event)=>set("scheduled_date",event.target.value)} /></label><label>Time window<select value={form.time_window} onChange={(event)=>set("time_window",event.target.value)}><option value="morning">Morning, 7am–11am</option><option value="midday">Midday, 11am–3pm</option><option value="evening">Evening, 3pm–7pm</option></select></label></div></>}
    {step===3 && <><h2>Set clear limits.</h2><fieldset className="budget-type-field"><legend>Budget type</legend><div className="budget-type-grid">{[["fixed","Fixed budget"],["quote","I need an estimate"],["hourly","Hourly"]].map(([value,label])=><label className={form.budget_type===value?"selected":""} key={value}><input type="radio" name="budget_type" value={value} checked={form.budget_type===value} onChange={(event)=>set("budget_type",event.target.value)} /><span>{label}</span></label>)}</div></fieldset><label>{form.budget_type === "quote" ? "Budget in GHS (optional)" : "Budget in GHS"}<input required={form.budget_type !== "quote"} type="number" min="1" value={form.budget} onChange={(event)=>set("budget",event.target.value)} inputMode="decimal" placeholder="e.g. 350" /></label><label>Phone for job updates<input required type="tel" value={form.contact_phone} onChange={(event)=>set("contact_phone",event.target.value)} placeholder="+233" /></label>{params.get("instant")==="1"&&<label className="check consent"><input type="checkbox" checked={form.instant_booking} onChange={(event)=>set("instant_booking",event.target.checked)}/> Book instantly at the artisan&apos;s starting price when this date is available.</label>}<label className="check consent"><input required type="checkbox" /> I will keep job changes and approvals in handEwork so support can review the record.</label></>}
    {error && <p className="form-error">{error}</p>}<div className="form-actions">{step>1 && <button type="button" className="button ghost-button" onClick={()=>setStep(step-1)}>Back</button>}<button className="button button-orange" disabled={busy}>{busy?"Submitting…":step<3?"Continue":"Create booking"}</button></div>
  </form></section></AppShell>;
}
