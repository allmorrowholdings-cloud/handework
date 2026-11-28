"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LocationPicker } from "../../components/location-picker";
import { findServices } from "../../../lib/service-catalogue";
import { Header } from "../../components/header";
import { accessToken, api, saveSession } from "../../../lib/api";

const initialForm = {
  first_name: "",
  last_name: "",
  phone: "",
  email: "",
  password: "",
  trade: "",
  secondary_services: "",
  years_experience: "",
  bio: "",
  city: "",
  coordinates: "",
  area: "",
  radius_km: "10",
};

import { useHydrated } from "../../components/use-hydrated";

type ArtisanForm = typeof initialForm;
type Session = { access_token: string; refresh_token?: string };

export default function JoinArtisan() {
  const ready = useHydrated();
  return ready ? <Application /> : <main><Header /><p className="shell" role="status">Opening your application...</p></main>;
}

function Application() {
  const router = useRouter();
  useEffect(() => {
    if (!accessToken()) return;
    const controller = new AbortController();
    api<{user: {role: string}}>("/v1/auth/me", { signal: controller.signal })
      .then(({user}) => { if (!controller.signal.aborted && user.role === "artisan") router.replace("/artisan/dashboard"); })
      .catch(() => {});
    return () => controller.abort();
  }, [router]);
  const [step, setStep] = useState(1);
  const [form, setForm] = useState<ArtisanForm>(() => {
    try { return {...initialForm, ...JSON.parse(sessionStorage.getItem("handework-application") || "{}"), password: ""}; }
    catch { return initialForm; }
  });
  const [query,setQuery]=useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const draft = {...form, password: ""};
    try { sessionStorage.setItem("handework-application", JSON.stringify(draft)); } catch { /* Private browsing can disable storage. */ }
  }, [form]);
  const set = (field: keyof ArtisanForm, value: string) =>
    setForm((current) => ({ ...current, [field]: value }));

  function continueStep(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!event.currentTarget.reportValidity()) return;
    if (step < 3) setStep((current) => current + 1);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!event.currentTarget.reportValidity()) return;
    if (step < 3) {
      setStep((current) => current + 1);
      return;
    }
    if (!form.coordinates) { setError("Confirm your service location using GPS or address search."); return; }
    const [latitude,longitude]=form.coordinates.split(",").map(Number);
    setBusy(true);
    try {
      const session = await api<Session>("/v1/auth/register-artisan", {
        method: "POST",
        body: JSON.stringify({ ...form, latitude, longitude, client: "web" }),
      });
      sessionStorage.removeItem("handework-application");
      saveSession(session.access_token, session.refresh_token);
      router.push("/artisan/verification");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not create profile");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="paper-page">
      <Header />
      <section className="join-hero">
        <div className="shell">
          
          <h1>Let&apos;s get your skill seen.</h1>
          <p>Join as an artisan, complete verification and choose the work you want to receive.</p>
        </div>
      </section>

      <section className="shell join-layout">
        <aside>
          <b>ARTISAN APPLICATION</b>
          <span className={step >= 1 ? "on" : ""}>01 / About you</span>
          <span className={step >= 2 ? "on" : ""}>02 / Your work</span>
          <span className={step >= 3 ? "on" : ""}>03 / Service area</span>
        </aside>

        <form className="join-form" onSubmit={step < 3 ? continueStep : submit}>
          {step === 1 && <>
            <h2>Who are you?</h2>
            <div className="two-fields">
              <label>First name<input required name="first_name" value={form.first_name} onChange={(e) => set("first_name", e.target.value)} autoComplete="given-name" /></label>
              <label>Last name<input required name="last_name" value={form.last_name} onChange={(e) => set("last_name", e.target.value)} autoComplete="family-name" /></label>
            </div>
            <label>Mobile number<input required name="phone" type="tel" placeholder="+233" value={form.phone} onChange={(e) => set("phone", e.target.value)} autoComplete="tel" /></label>
            <label>Email address<input required name="email" type="email" value={form.email} onChange={(e) => set("email", e.target.value)} autoComplete="email" /></label>
            <label>Create password
              <span className="password-field">
                <input required minLength={12} maxLength={128} name="password" type={showPassword ? "text" : "password"} value={form.password} onChange={(e) => set("password", e.target.value)} autoComplete="new-password" />
                <button type="button" className="password-toggle" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? "Hide" : "Show"}</button>
              </span>
            </label>
          </>}

          {step === 2 && <>
            <h2>What work do you do?</h2>
            <label>Primary profession<input required name="trade" list="profession-options" placeholder="Search or enter your profession" value={form.trade} onChange={e=>set("trade",e.target.value)}/></label><datalist id="profession-options">{findServices(form.trade).slice(0,30).map(name=><option key={name} value={name}/>)}</datalist>
            <fieldset className="hw-capability-picker"><legend>Specific services you offer</legend><label>Find a service<input type="search" value={query} onChange={e=>setQuery(e.target.value)}/></label><div className="hw-capability-list">{form.secondary_services.split(",").filter(Boolean).map(v=>v.trim()).map(name=><button type="button" key={name} onClick={()=>set("secondary_services",form.secondary_services.split(",").map(v=>v.trim()).filter(v=>v!==name).join(", "))}>{name} ×</button>)}</div>{query.trim()&&<div className="hw-capability-list">{findServices(query).slice(0,12).map(name=><button type="button" key={name} onClick={()=>{set("secondary_services",[...new Set([...form.secondary_services.split(",").map(v=>v.trim()).filter(Boolean),name])].join(", "));setQuery("")}}>Add {name}</button>)}</div>}</fieldset>
            <label>Years of experience<input required min="0" name="years_experience" type="number" value={form.years_experience} onChange={(e) => set("years_experience", e.target.value)} /></label>
            <label>Tell customers about your work<textarea required name="bio" rows={5} value={form.bio} onChange={(e) => set("bio", e.target.value)} /></label>
          </>}

          {step === 3 && <>
            <h2>Where can you work?</h2>
            <div className="two-fields">
              <label>City or town<input required value={form.city} onChange={e=>setForm(v=>({...v,city:e.target.value,coordinates:""}))}/></label>
              <label>Home area<input required name="area" value={form.area} onChange={e=>setForm(v=>({...v,area:e.target.value,coordinates:""}))} /></label>
            </div>
            <LocationPicker value={form.coordinates} onSelect={(coordinates)=>set("coordinates",coordinates)}/><p>Confirm that the selected location matches your city and area.</p>
            <label>Travel radius<select name="radius_km" value={form.radius_km} onChange={(e) => set("radius_km", e.target.value)}><option value="3">Up to 3 km</option><option value="10">Up to 10 km</option><option value="25">Up to 25 km</option><option value="50">Up to 50 km</option></select></label>
            <label className="check consent"><input required type="checkbox" /> I agree to identity and trade verification before my profile goes live.</label>
          </>}

          {error && <p className="form-error" role="alert">{error}</p>}
          <div className="form-actions">
            {step > 1 && <button type="button" className="button ghost-button" onClick={() => setStep((current) => current - 1)}>Back</button>}
            <button className="button button-orange" disabled={busy}>{busy ? "Creating profile…" : step < 3 ? "Continue" : "Create artisan profile"}</button>
          </div>
          <p className="auth-switch">Already applied? <Link href="/auth/sign-in">Sign in</Link></p>
        </form>
      </section>
    </main>
  );
}
