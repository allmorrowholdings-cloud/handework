"use client";

import { ChangeEvent, FormEvent, Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { LocationPicker } from "../../components/location-picker";
import { Header } from "../../components/header";
import { AuthForm } from "../../components/auth-form";
import { ServiceSelect } from "../../components/service-select";
import { accessToken, api } from "../../../lib/api";

function bookingToday() {
  return new Date().toISOString().slice(0, 10);
}

const initial = { coordinates:"", requestKey:"", service:"", description:"", address:"", area:"", city:"Accra", scheduled_date:"", time_window:"morning", budget_type:"quote", budget:"", contact_phone:"", instant_booking:false };

export default function NewBookingPage() {
  return <Suspense fallback={<p className="shell" role="status">Loading job request…</p>}><NewBookingForm /></Suspense>;
}

function NewBookingForm() {
  const params = useSearchParams();
  const router = useRouter();
  const [step, setStep] = useState(() => {
    try { return Math.max(1, Math.min(3, JSON.parse(sessionStorage.getItem("handework-job:" + params.toString()) || "{}").step || 1)); } catch { return 1; }
  });
  const draftKey = "handework-job:" + params.toString();
  const [form, setForm] = useState(() => {
    const defaults = {...initial, coordinates:params.get("coordinates")??"", requestKey: crypto.randomUUID(), description: params.get("problem") ?? "", area: params.get("area") ?? params.get("location") ?? params.get("coordinates") ?? "", service: params.get("service") ?? (params.get("problem") ? "Help me choose" : "")};
    try { return {...defaults, ...JSON.parse(sessionStorage.getItem(draftKey) || "{}").form} as typeof initial; } catch { return defaults; }
  });
  useEffect(() => {
    try { sessionStorage.setItem(draftKey, JSON.stringify({form, step})); } catch { /* Storage can be disabled. */ }
  }, [form, step, draftKey]);
  const [media, setMedia] = useState<File[]>([]);
  const [error, setError] = useState("");
  const [stepOneErrors, setStepOneErrors] = useState<{service?:string;description?:string}>({});
  const [busy, setBusy] = useState(false);
  const [auth, setAuth] = useState<"sign-in" | "create" | null>(null);
  const [artisan, setArtisan] = useState(params.get("artisan") ?? "");
  const [matches, setMatches] = useState<{id: string; display_name: string}[]>([]);
  const [matchStatus, setMatchStatus] = useState("Checking artisan availability...");
  const [createdId, setCreatedId] = useState("");
  const [uploaded, setUploaded] = useState(0);
  const coordinates = form.coordinates;
  useEffect(() => {
    if (step !== 3 || params.get("artisan")) return;
    const query = new URLSearchParams({service: form.service === "Help me choose" ? form.description : form.service, location: form.area + ", " + form.city, date: form.scheduled_date});
    if (coordinates) query.set("coordinates", coordinates);
    const controller = new AbortController();
    api<{items: {id: string; display_name: string}[]}>(`/v1/artisans/search?${query}`, {signal: controller.signal})
      .then(({items}) => { if (!controller.signal.aborted) { setMatches(items); setMatchStatus(items.length ? "" : "No professional matches this date. An unassigned request stays in My jobs. Contact support if you need help finding someone."); } })
      .catch(() => { if (!controller.signal.aborted) setMatchStatus("Matching is temporarily unavailable. You can go back and try again, or save an unassigned request in My jobs."); });
    return () => controller.abort();
  }, [step, form.description, form.service, form.city, form.area, form.scheduled_date, coordinates, params]);
  useEffect(() => {
    if (auth) document.querySelector<HTMLInputElement>(".request-auth input")?.focus();
  }, [auth]);
  const set = (field:string, value:string|boolean) => setForm((current) => ({ ...current, [field]: value }));
  function files(event: ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(event.target.files ?? []);
    setError(selected.length > 5 ? "The first five files were added. Choose again to change them." : "");
    setMedia(selected.slice(0, 5));
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const today = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Africa/Accra",
      year: "numeric",
      month: "2-digit",
      day: "2-digit"
    }).format(new Date());

    if (step >= 2 && (!form.scheduled_date || form.scheduled_date < today)) {
      setError("Choose today or a future date for your job.");
      setStep(2);
      return;
    }
    if (step === 1) {
      const errors = {
        service: form.service.trim() ? undefined : "Choose a service before continuing.",
        description: form.description.trim() ? undefined : "Describe the job before continuing.",
      };
      setStepOneErrors(errors);
      if (errors.service || errors.description) return;
    }
    if (step === 2 && (!form.area.trim() || !form.address.trim())) { setError("Enter the job address and area before continuing."); return; }
    if (step === 2 && !params.get("artisan")) {
      setMatches([]);
      setArtisan("");
      setMatchStatus("Checking artisan availability...");
    }
    if (step < 3) { setStep(step + 1); return; }
    if (!accessToken()) { setAuth("sign-in"); return; }
    if (auth || busy) return;
    setBusy(true);
    try {
      let id = createdId;
      if (!id) {
        const booking = await api<{id:string}>("/v1/bookings", { method:"POST", headers:{"Idempotency-Key":form.requestKey}, body:JSON.stringify({ ...form, smart_dispatch:artisan==="smart", artisan_id: artisan==="smart"?undefined:artisan || undefined }) });
        id = booking.id;
        setCreatedId(id);
      }
      for (let i = uploaded; i < media.length; i++) {
        const upload = new FormData(); upload.append("file", media[i]); upload.append("purpose", "booking_media"); upload.append("booking_id", id);
        await api("/v1/uploads", { method:"POST", body:upload });
        setUploaded(i + 1);
      }
      sessionStorage.removeItem(draftKey);
      router.push(`/bookings/${id}`);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not create booking"); }
    finally { setBusy(false); }
  }
  return <main><Header /><div className="shell public-request"><header><nav className="booking-breadcrumbs" aria-label="Breadcrumb"><Link href="/marketplace">Services</Link><span aria-hidden="true">/</span><span aria-current="page">Request a job</span></nav><h1>Request skilled work</h1><p>Nothing is charged until the scope and artisan are confirmed.</p></header><section className="app-content narrow-content"><div className="booking-progress"><span className={step>=1?"on":""}>1. Work</span><span className={step>=2?"on":""}>2. Place & time</span><span className={step>=3?"on":""}>3. Budget & review</span></div><form className="app-card booking-form" onSubmit={submit}>
    {step===1 && <><h2>What needs doing?</h2><label>Service category<ServiceSelect allowUnknown value={form.service} onChange={value => { set("service", value); setStepOneErrors(current => ({...current, service: undefined})); }} />{stepOneErrors.service && <small className="form-error" role="alert">{stepOneErrors.service}</small>}</label><label>Job details<textarea required aria-invalid={Boolean(stepOneErrors.description)} aria-describedby={stepOneErrors.description ? "job-description-error" : undefined} value={form.description} onChange={(event)=>{ set("description",event.target.value); if(event.target.value.trim())setStepOneErrors(current=>({...current,description:undefined})); }} rows={6} placeholder="Describe the problem or result you need. Include measurements or useful details." />{stepOneErrors.description && <small id="job-description-error" className="form-error" role="alert">{stepOneErrors.description}</small>}</label><label className="upload-zone">Photos or short video<input type="file" multiple accept="image/jpeg,image/png,image/webp,video/mp4" onChange={files} /><span>{media.length ? `${media.length} file${media.length===1?"":"s"} selected` : "Add up to five photos or MP4 clips. Reselect attachments after refreshing."}</span></label></>}
    {step===2 && <><h2>Where and when?</h2><LocationPicker value={coordinates} onSelect={(pin,label)=>setForm(current=>({...current,coordinates:pin,address:label??current.address}))}/><label>Job address<input required value={form.address} onChange={(event)=>set("address",event.target.value)} placeholder="House number, street or landmark" /></label><div className="two-fields"><label>Area<input required value={form.area} onChange={(event)=>set("area",event.target.value)} placeholder="e.g. East Legon" /></label><label>City<select value={form.city} onChange={(event)=>set("city",event.target.value)}><option>Accra</option><option>Kumasi</option><option>Tema</option><option>Takoradi</option><option>Cape Coast</option><option>Tamale</option></select></label></div><div className="two-fields"><label>Date<input required type="date" min={new Intl.DateTimeFormat("en-CA", {
      timeZone: "Africa/Accra",
      year: "numeric",
      month: "2-digit",
      day: "2-digit"
    }).format(new Date())} value={form.scheduled_date} onChange={(event)=>set("scheduled_date",event.target.value)} /></label><label>Time window<select value={form.time_window} onChange={(event)=>set("time_window",event.target.value)}><option value="morning">Morning, 7am–11am</option><option value="midday">Midday, 11am–3pm</option><option value="evening">Evening, 3pm–7pm</option></select></label></div></>}
    {step===3 && <><h2>Budget and review</h2><p><strong>{form.service}</strong> &middot; {form.description}</p><p>{form.address}, {form.area}, {form.city} &middot; {form.scheduled_date}, {form.time_window}</p>
      {!params.get("artisan") && <label>Artisan<select value={artisan} onChange={event => setArtisan(event.target.value)}><option value="">Save without a professional</option>{coordinates&&<option value="smart">Smart Dispatch ? request the highest ranked available artisan</option>}{matches.map(person => <option key={person.id} value={person.id}>{person.display_name}</option>)}</select></label>}
      {!params.get("artisan") && matchStatus && <p role="status">{matchStatus}</p>}<fieldset className="budget-type-field"><legend>Budget type</legend><div className="budget-type-grid">{[["fixed","Fixed budget"],["quote","I need an estimate"],["hourly","Hourly"]].map(([value,label])=><label className={form.budget_type===value?"selected":""} key={value}><input type="radio" name="budget_type" value={value} checked={form.budget_type===value} onChange={(event)=>set("budget_type",event.target.value)} /><span>{label}</span></label>)}</div></fieldset><label>{form.budget_type === "quote" ? "Budget in GHS (optional)" : "Budget in GHS"}<input required={form.budget_type !== "quote"} type="number" min="1" value={form.budget} onChange={(event)=>set("budget",event.target.value)} inputMode="decimal" placeholder="e.g. 350" /></label><label>Phone for job updates<input required type="tel" value={form.contact_phone} onChange={(event)=>set("contact_phone",event.target.value)} placeholder="+233" /></label>{params.get("instant")==="1"&&<label className="check consent"><input type="checkbox" checked={form.instant_booking} onChange={(event)=>set("instant_booking",event.target.checked)}/> Book instantly at the artisan&apos;s starting price when this date is available.</label>}<label className="check consent"><input required type="checkbox" /> I will keep job changes and approvals in handEwork so support can review the record.</label></>}
    {error && <p className="form-error" role="alert">{error}</p>}<div className="form-actions">{step>1 && !createdId && <button type="button" className="button ghost-button" onClick={()=>setStep(step-1)}>Back</button>}<button className="button button-orange" disabled={busy || Boolean(auth)}>{busy?"Submitting…":step<3?"Continue":createdId?"Finish uploading":"Confirm request"}</button></div>
  </form>
    {auth && <section className="app-card request-auth" aria-label="Account for this booking"><h2>{auth === "sign-in" ? "Sign in to send your request" : "Create an account to send your request"}</h2><p>Your job details and photos are ready. Confirm your request after signing in.</p>
      <AuthForm key={auth} mode={auth} onAuthenticated={() => setAuth(null)} onSwitch={() => setAuth(auth === "create" ? "sign-in" : "create")} />
    </section>}
  </section></div></main>;
}
