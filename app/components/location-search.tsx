"use client";

import { FormEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../lib/api";
import ghPlaces from "../../lib/ghana-places.json";
import { ServiceSelect } from "./service-select";

type Town = { name: string };
type District = { id: string; name: string; towns: Town[] };
type Region = { id: string; name: string; districts: District[] };
const regions: Region[] = ghPlaces;
type LocationResult = { label: string; lat: number; lon: number };

export function LocationSearch({ compact = false, initialService = "", initialLocation = "", initialCoordinates = "" }: { compact?: boolean; initialService?: string; initialLocation?: string; initialCoordinates?: string }) {
  const router = useRouter();
  const [describe, setDescribe] = useState(false);
  const [problem, setProblem] = useState("");
  const [service, setService] = useState(initialService);
  const [location, setLocation] = useState(initialLocation || (initialCoordinates ? "GPS location selected" : ""));
  const [coordinates, setCoordinates] = useState(initialCoordinates);
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState("");
  const [regionId, setRegionId] = useState("");
  const [districtId, setDistrictId] = useState("");
  const locationRequest = useRef(0);
  const region = regions.find(item => item.id === regionId);
  const district = region?.districts.find(item => item.id === districtId);

  async function reverseLocation(lat: number, lon: number, request: number) {
    try {
      const response = await api<{items: LocationResult[]}>(
        `/v1/locations/reverse?coordinates=${encodeURIComponent(`${lat},${lon}`)}`
      );
      if (locationRequest.current !== request) return;
      const name = response.items?.[0]?.label;
      setLocation(name || "Location confirmed");
      setLocationError("");
    } catch {
      if (locationRequest.current !== request) return;
      setLocation("Location confirmed");
      setLocationError("");
    } finally {
      if (locationRequest.current === request) setLocating(false);
    }
  }

  function locate() {
    if (!window.isSecureContext || !navigator.geolocation) {
      setLocationError("GPS is unavailable here. Choose a Ghana region and town, or type a landmark.");
      return;
    }
    const request = ++locationRequest.current;
    setLocating(true);
    setLocationError("handEwork is requesting location access. Please choose Allow when your browser asks.");
    navigator.geolocation.getCurrentPosition(({ coords }) => {
      if (locationRequest.current !== request) return;
      const {latitude:lat, longitude:lon} = coords;
      setCoordinates(`${lat},${lon}`);
      setLocation("Location confirmed"); setLocationError(""); setLocating(false);
      void reverseLocation(lat,lon,request);
    }, error => {
      if (locationRequest.current !== request) return;
      setLocating(false);
      const android = /Android/i.test(navigator.userAgent);
      const iphone = /iPhone|iPad|iPod/i.test(navigator.userAgent);
      const permissionHelp = android
        ? "Location is blocked for this site. In your Android browser, open site settings and allow Location, then tap Use GPS again. Check your phone's Location setting too. Or select a town below."
        : iphone
          ? "Location is blocked. On iPhone, allow Location for this website in Safari's Website Settings (or your browser's site permissions), then tap Use GPS again. Check iPhone Settings > Privacy & Security > Location Services too. Or select a town below."
          : "Location is blocked for this site. Allow Location in your browser's site settings, then tap Use GPS again, or select a town below.";
      setLocationError(error.code === 1
        ? permissionHelp
        : error.code === 3
          ? "GPS timed out. Try Use GPS again or select a town below."
          : "Your device could not provide a location. Please check location settings or choose a town below.");
    }, {enableHighAccuracy: false, maximumAge: 60000, timeout: 15000});
  }

  function updateRegion(id: string) {
    locationRequest.current++;
    setLocating(false); setRegionId(id); setDistrictId("");
    setCoordinates(""); setLocation(""); setLocationError("");
  }
  function updateDistrict(id: string) {
    locationRequest.current++;
    setLocating(false); setDistrictId(id);
    setCoordinates(""); setLocation(""); setLocationError("");
  }
  function chooseTown(name: string) {
    if (!region || !district) return;
    locationRequest.current++;
    setLocating(false);
    setCoordinates("");
    setLocation(`${name}, ${district.name}, ${region.name}, Ghana`);
    setLocationError("");
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locating) return;
    if (describe && !problem.trim()) { setLocationError("Describe what you need help with."); return; }
    if ((!describe && !service) || (!location.trim() && !coordinates)) {
      setLocationError(!service && !location.trim() ? "Choose a service and job location." : !service ? "Choose a service to continue." : "Choose a job location or use GPS to continue.");
      return;
    }
    const query = new URLSearchParams();
    if (describe) query.set("problem",problem.trim());
    else query.set("service", service.trim());
    if (coordinates) query.set("coordinates",coordinates);
    else query.set("location",location.trim());
    router.push(`${describe || !compact ? "/bookings/new" : "/marketplace"}?${query.toString()}`);
  }

  return <form className={compact ? "finder compact" : "finder"} onSubmit={submit} noValidate>
    <label className="finder-service"><span>What do you need done?</span>
      {describe ? <input value={problem} onChange={e=>setProblem(e.target.value)} placeholder="e.g. My tap is leaking"/> : <ServiceSelect value={service} onChange={value=>{setService(value);setLocationError("");}}/>}
      <button className="finder-mode" type="button" onClick={()=>{setDescribe(!describe);setLocationError("");}}>{describe ? "Choose a service" : "Describe a problem"}</button>
    </label>
    <div className="finder-place">
      <label className="finder-place-input"><span>Where is the job?</span>
        <input className={coordinates ? "gps-location-confirmed" : undefined} value={location} onChange={e=>{locationRequest.current++;setLocating(false);setCoordinates("");setLocation(e.target.value);setLocationError("");}} placeholder="Town, neighbourhood or landmark" aria-label="Job location" />
        <button type="button" className="locate" onClick={locate} disabled={locating} aria-label="Use GPS to find the job location">{locating ? "Finding..." : "Use GPS"}</button>
      </label>
      <details className="finder-browse">
        <summary>Choose region, district and town</summary>
        <div className="finder-admin-grid">
          <select aria-label="Ghana region" value={regionId} onChange={e=>updateRegion(e.target.value)}>
            <option value="">Choose region</option>
            {regions.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <select aria-label="Ghana district" value={districtId} disabled={!region} onChange={e=>updateDistrict(e.target.value)}>
            <option value="">Choose district</option>
            {region?.districts.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <select aria-label="Ghana town" value="" disabled={!district} onChange={e=>chooseTown(e.target.value)}>
            <option value="">Choose town</option>
            {district?.towns.map((item,i)=><option key={`${item.name}-${i}`} value={item.name}>{item.name}</option>)}
          </select>
        </div>
        <p>Can't find your community? Enter the town or nearest landmark above.</p>
      </details>
    </div>
    {locationError && <p className="finder-location-error" role="status">{locationError}</p>}
    <button type="submit" className="finder-submit" disabled={locating}>Find an artisan</button>
  </form>;
}