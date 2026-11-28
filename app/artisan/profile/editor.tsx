"use client";
import { LocationPicker } from "../../components/location-picker";
import Image from "next/image";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import type { ChangeEvent } from "react";
import { api } from "../../../lib/api";

type Profile = { latitude?: number | null; longitude?: number | null; display_name: string; trade: string; secondary_services?: string; bio?: string; starting_price?: number; radius_km: number; languages?: string; city?: string; area?: string; instant_booking: boolean; avatar_url?: string | null; verification_status?: string; available?: boolean };

export function ProfileEditor() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { api<{ artisan: Profile }>("/v1/artisans/me").then(body => setProfile(body.artisan)).catch(error => setNotice(error.message)); }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!profile) return; setBusy(true); setNotice("");
    try { const body = await api<{ artisan: Profile }>("/v1/artisans/me", { method: "PATCH", body: JSON.stringify(profile) }); setProfile(body.artisan); setNotice("Work profile saved."); }
    catch (error) { setNotice(error instanceof Error ? error.message : "Profile could not be saved"); }
    finally { setBusy(false); }
  }
  async function avatar(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; if (!file || !profile) return; setBusy(true); setNotice("");
    try { const form = new FormData(); form.set("purpose", "profile_picture"); form.set("file", file); const saved = await api<{ url: string }>("/v1/uploads", { method: "POST", body: form }); setProfile(current => current ? { ...current, avatar_url: saved.url } : current); setNotice("Profile picture uploaded."); }
    catch (error) { setNotice(error instanceof Error ? error.message : "Profile picture could not be uploaded"); }
    finally { setBusy(false); event.target.value = ""; }
  }
  if (!profile) return <div className="loading-line"><span />{notice || "Loading work profile…"}</div>;
  const set = (field: keyof Profile, value: string | number | boolean) => setProfile(current => current ? { ...current, [field]: value } : current);
  return <form className="app-card settings-form" onSubmit={submit}>
    <div className="data-note" role="status">
      {profile.verification_status !== "approved" ? (
        <>
          <strong>Your profile is not yet publicly listed.</strong>
          <p>
            Verification status: {profile.verification_status ?? "not confirmed"}.
            Complete your checks and await an administrator&apos;s approval.
          </p>
          <Link href="/artisan/verification">Manage verification</Link>
        </>
      ) : !profile.available ? (
        <>
          <strong>Your profile is approved but not currently available for search.</strong>
          <p>
            Save your working hours to enable availability.
          </p>
          <Link href="/artisan/availability">Manage availability</Link>
        </>
      ) : profile.latitude == null || profile.longitude == null ? (
        <>
          <strong>Your profile is approved and accepting work.</strong>
          <p>
            Add a service-location pin so nearby customers can find you
            in distance-based searches.
          </p>
        </>
      ) : (
        <>
          <strong>Your profile is approved and accepting work.</strong>
          <p>
            Customers can discover you when your trade, service area,
            distance and availability match their search.
          </p>
        </>
      )}
    </div>
    <div className="profile-banner"><div className="profile-avatar">{profile.avatar_url ? <Image src={profile.avatar_url} alt="Profile" width={80} height={80} unoptimized /> : profile.display_name.slice(0, 1)}</div><div><h2>Public artisan profile</h2><p>Approved information is shown to customers.</p><label>Profile picture<input type="file" accept="image/jpeg,image/png,image/webp" onChange={avatar} /></label></div></div>
    <label>Professional display name<input value={profile.display_name} onChange={event => set("display_name", event.target.value)} /></label>
    <label>Main trade<input value={profile.trade} onChange={event => set("trade", event.target.value)} /></label>
    <label>Specific services offered (comma-separated)<input value={profile.secondary_services ?? ""} onChange={event => set("secondary_services", event.target.value)} placeholder="AC repair, CCTV installation" /></label><p>Only list work you are qualified to perform. Profile approval does not certify every listed service.</p><label>Short work introduction<textarea rows={5} value={profile.bio ?? ""} onChange={event => set("bio", event.target.value)} /></label>
    <div className="two-fields"><label>Starting price (GHS)<input min="0" type="number" value={profile.starting_price ?? ""} onChange={event => set("starting_price", Number(event.target.value))} /></label><label>Service radius (km)<input min="1" max="100" type="number" value={profile.radius_km} onChange={event => set("radius_km", Number(event.target.value))} /></label></div>
    <LocationPicker value={profile.latitude != null && profile.longitude != null ? `${profile.latitude},${profile.longitude}` : ""} onSelect={pin => { const [latitude, longitude] = pin.split(",").map(Number); setProfile(current => current ? { ...current, latitude, longitude } : current); }} />
    <label>Languages<input value={profile.languages ?? ""} onChange={event => set("languages", event.target.value)} placeholder="English, Twi, Ga…" /></label>
    <label className="setting-row"><span><b>Instant booking</b><small>Use your starting price only on dates marked available</small></span><input type="checkbox" checked={profile.instant_booking} onChange={event => set("instant_booking", event.target.checked)} /></label>
    {notice && <p className="data-note" role="status">{notice}</p>}<button className="button button-orange" disabled={busy}>{busy ? "Saving…" : "Save profile"}</button>
  </form>;
}
