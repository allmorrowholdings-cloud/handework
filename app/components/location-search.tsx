"use client";

import { FormEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { ServiceSelect } from "./service-select";

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
        setLocation(`${coords.latitude.toFixed(4)}, ${coords.longitude.toFixed(4)}`);
        setLocating(false);
      },
      (error) => {
        if (request !== locationRequest.current) return;
        setLocationError(error.code === 1
          ? "Allow location for this site in your browser, or enter your area below."
          : error.code === 3
            ? "Finding your location took too long. Try again or enter your area."
            : "Your device could not determine its location. Check location services or enter your area.");
        setLocating(false);
      },
      { enableHighAccuracy: false, maximumAge: 60_000, timeout: 15_000 }
    );
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (locating) return;
    if (!service || (!location.trim() && !coordinates)) {
      setLocationError(!service && !location.trim() ? "Choose a service and enter the job location." : !service ? "Choose a service to continue." : "Enter the job location or use GPS to continue.");
      (event.currentTarget as HTMLFormElement).querySelector<HTMLElement>(!service ? "select" : "input")?.focus();
      return;
    }
    const query = new URLSearchParams();
    if (service.trim()) query.set("service", service.trim());
    if (!coordinates && location.trim()) query.set("location", location.trim());
    if (coordinates) query.set("coordinates", coordinates);
    router.push(`${compact && initialService ? "/marketplace" : "/bookings/new"}?${query.toString()}`);
  }

  return <form className={compact ? "finder compact" : "finder"} onSubmit={submit} noValidate>
    <label><span>What needs doing?</span><ServiceSelect value={service} onChange={value => { setService(value); setLocationError(""); }} /></label>
    <label><span>Where is the job?</span><input required value={location} onChange={(e) => { locationRequest.current++; setLocating(false); setLocation(e.target.value); setCoordinates(""); setLocationError(""); }} placeholder="e.g. Osu, Accra" aria-label="Job location" aria-describedby={locationError ? "finder-location-error" : undefined} /><button type="button" className="locate" disabled={locating} onClick={locate}>{locating ? "Locating…" : "Use GPS"}</button></label>
    {locationError && <p id="finder-location-error" className="finder-location-error" role="status">{locationError}</p>}
    <button className="finder-submit" type="submit" disabled={locating}>Find an artisan</button>
  </form>;
}
