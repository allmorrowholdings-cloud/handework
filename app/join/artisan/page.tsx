"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Header } from "../../components/header";
import { api, saveSession } from "../../../lib/api";

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
  city: "Accra",
  area: "",
  radius_km: "10",
};

type ArtisanForm = typeof initialForm;
type Session = { access_token: string; refresh_token?: string };

export default function JoinArtisan() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState<ArtisanForm>(initialForm);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

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
    setBusy(true);
    try {
      const session = await api<Session>("/v1/auth/register-artisan", {
        method: "POST",
        body: JSON.stringify(form),
      });
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
          
          <h1>Put your skill<br />where work can find it.</h1>
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
                <input required minLength={8} name="password" type={showPassword ? "text" : "password"} value={form.password} onChange={(e) => set("password", e.target.value)} autoComplete="new-password" />
                <button type="button" className="password-toggle" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? "Hide" : "Show"}</button>
              </span>
            </label>
          </>}

          {step === 2 && <>
            <h2>What work do you do?</h2>
            <label>Main trade<input required name="trade" placeholder="e.g. plumber, dressmaker, welder" value={form.trade} onChange={(e) => set("trade", e.target.value)} /></label>
            <label>Other services<input name="secondary_services" placeholder="Separate with commas" value={form.secondary_services} onChange={(e) => set("secondary_services", e.target.value)} /></label>
            <label>Years of experience<input required min="0" name="years_experience" type="number" value={form.years_experience} onChange={(e) => set("years_experience", e.target.value)} /></label>
            <label>Tell customers about your work<textarea required name="bio" rows={5} value={form.bio} onChange={(e) => set("bio", e.target.value)} /></label>
          </>}

          {step === 3 && <>
            <h2>Where can you work?</h2>
            <div className="two-fields">
              <label>City<select name="city" value={form.city} onChange={(e) => set("city", e.target.value)}><option>Accra</option><option>Kumasi</option><option>Tema</option><option>Takoradi</option><option>Cape Coast</option><option>Tamale</option></select></label>
              <label>Home area<input required name="area" value={form.area} onChange={(e) => set("area", e.target.value)} /></label>
            </div>
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
