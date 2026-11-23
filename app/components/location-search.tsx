"use client";

import { FormEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";

export function LocationSearch({ compact = false, initialService = "", initialLocation = "", initialCoordinates = "" }: { compact?: boolean; initialService?: string; initialLocation?: string; initialCoordinates?: string }) {
  const router = useRouter();
  const [service, setService] = useState(initialService);
  const [location, setLocation] = useState(initialLocation || (initialCoordinates ? "Current location" : ""));
  const [locating, setLocating] = useState(false);
  const [coordinates, setCoordinates] = useState(initialCoordinates);
  const [locationError, setLocationError] = useState("");
  const locationRequest = useRef(0);

  function locate() {
    if (!window.isSecureContext || !navigator.geolocation) {
      setLocationError("GPS is unavailable here. Enter your area or landmark instead.");
      return;
    }
    const request = ++locationRequest.current;
    setLocationError("");
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        if (request !== locationRequest.current) return;
        setCoordinates(`${coords.latitude},${coords.longitude}`);
        setLocation("Current location");
        setLocating(false);
      },
      (error) => {
        if (request !== locationRequest.current) return;
        setLocationError(error.code === 1 ? "Location permission was denied. Allow it in your browser or enter your area." : "Could not get your location. Try again or enter your area.");
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (locating) return;
    const query = new URLSearchParams();
    if (service.trim()) query.set("service", service.trim());
    if (!coordinates && location.trim()) query.set("location", location.trim());
    if (coordinates) query.set("coordinates", coordinates);
    router.push(`/marketplace?${query.toString()}`);
  }

  return <form className={compact ? "finder compact" : "finder"} onSubmit={submit}>
    <label><span>What needs doing?</span><input value={service} onChange={(e) => setService(e.target.value)} placeholder="e.g. Plumbing" aria-label="Service needed" /></label>
    <label><span>Where is the job?</span><input value={location} onChange={(e) => { locationRequest.current++; setLocating(false); setLocation(e.target.value); setCoordinates(""); setLocationError(""); }} placeholder="e.g. Osu, Accra" aria-label="Job location" aria-describedby={locationError ? "finder-location-error" : undefined} /><button type="button" className="locate" disabled={locating} onClick={locate}>{locating ? "Locating…" : "Use GPS"}</button></label>
    {locationError && <p id="finder-location-error" className="finder-location-error" role="status">{locationError}</p>}
    <button className="finder-submit" type="submit" disabled={locating}>Find an artisan</button>
  </form>;
}
