"use client";

import { ChangeEvent, Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import ghanaPlaces from "../../lib/ghana-places.json";
import { catalogue, findServices, serviceNames } from "../../lib/service-catalogue";
import { api } from "../../lib/api";

type Professional = { id: string; display_name: string; trade?: string; area?: string; city?: string; distance_km?: number; verification_status?: string };
type UserResponse = { user: { phone?: string } };
const steps = ["Service", "Details", "Photos", "Location", "Schedule", "Budget", "Match", "Review"];
const regions = ghanaPlaces as { name:string; districts:{name:string; towns:{name:string}[]}[] }[];
const initial = {service:"",description:"",address:"",area:"",city:"",region:"",district:"",town:"",coordinates:"",date:"",time_window:"morning",start_time:"09:00",drive_url:"",budget_type:"quote",budget:"",phone:""};

export function AppBookingFlow() {
  return <Suspense fallback={<p role="status">Opening your booking…</p>}><BookingEntry/></Suspense>;
}
function BookingEntry(){
  const params=useSearchParams();
  const requested=params.get("service")||"";
  const service=serviceNames.includes(requested)||requested==="Help me choose"?requested:"";
  return <BookingFlow key={service} requestedService={service}/>;
}
function BookingFlow({requestedService}:{requestedService:string}) {
  const suffix=requestedService?":"+encodeURIComponent(requestedService):"";
  const draftStorage="hw-app-booking-draft"+suffix;
  const requestStorage="hw-app-booking-request"+suffix;
  const router = useRouter();
  const [step,setStep] = useState(()=>{if(typeof window==="undefined")return 0;try{return Math.max(0,Math.min(7,Number(JSON.parse(sessionStorage.getItem(draftStorage)||"{}").step)||0))}catch{return 0}});
  const [form,setForm] = useState<typeof initial>(()=>{const defaults={...initial,service:requestedService};if(typeof window==="undefined")return defaults;try{return {...defaults,...JSON.parse(sessionStorage.getItem(draftStorage)||"{}").form}}catch{return defaults}});
  const [media,setMedia] = useState<File[]>([]);
  const [matches,setMatches] = useState<Professional[]>([]);
  const [selected,setSelected] = useState("");
  const [loading,setLoading] = useState(false);
  const [matching,setMatching] = useState(false);
  const [matchingError,setMatchingError] = useState("");
  const [error,setError] = useState("");
  const [gpsBusy,setGpsBusy]=useState(false);
  const [gpsVerified,setGpsVerified]=useState(false);
  const [draftKey] = useState(()=>{if(typeof window==="undefined")return "";try{const saved=sessionStorage.getItem(requestStorage);if(saved)return saved;const id=crypto.randomUUID();sessionStorage.setItem(requestStorage,id);return id}catch{return crypto.randomUUID()}});
  useEffect(()=>{try{sessionStorage.setItem(draftStorage,JSON.stringify({step,form}))}catch{}},[step,form,draftStorage]);
  const region = regions.find(r=>r.name===form.region);
  const district = region?.districts.find(d=>d.name===form.district);
  const [serviceSearch,setServiceSearch]=useState("");
  const [category,setCategory]=useState("");
  const [limit,setLimit]=useState(24);
  const serviceOptions = useMemo(()=>findServices(serviceSearch).filter(name=>!category||catalogue.some(row=>row.category===category&&row.name===name)),[serviceSearch,category]);
  const location = [form.area || form.town, form.city || form.region].filter(Boolean).join(", ");
  const today = new Date().toLocaleDateString("en-CA",{timeZone:"Africa/Accra"});
  const update = (key:keyof typeof initial,value:string) => setForm(old=>({...old,[key]:value}));

  useEffect(()=>{let active=true;api<UserResponse>("/v1/auth/me").then(r=>{if(active&&r.user.phone)setForm(v=>({...v,phone:v.phone||r.user.phone||""}))}).catch(()=>{});return()=>{active=false}},[]);
  useEffect(()=>{
    if(step!==6)return;
    const controller=new AbortController();
    queueMicrotask(()=>{if(!controller.signal.aborted){setMatching(true);setMatchingError("");setSelected("");}});
    const query=new URLSearchParams({service:form.service,location,date:form.date});
    if(form.coordinates)query.set("coordinates",form.coordinates);
    if(form.date)query.set("start_time",form.start_time);
    api<{items:Professional[]}>(`/v1/artisans/search?${query}`,{signal:controller.signal}).then(r=>{
      if(controller.signal.aborted)return;
      setMatches(r.items);setMatching(false);
    }).catch(()=>{if(!controller.signal.aborted){setMatches([]);setMatching(false);setMatchingError("Matching is unavailable right now. You can still save your request without selecting a professional.")}});
    return()=>controller.abort();
  },[step,form.service,form.date,form.start_time,form.coordinates,location]);

  function next(){
    setError("");
    if(step===0&&!form.service){setError("Choose a service to continue.");return}
    if(step===1&&!form.description.trim()){setError("Tell us what you need done.");return}
    if(step===3&&(!form.address.trim()||!form.area.trim()||!form.city.trim())){setError("Add your town or area and a nearby address or landmark.");return}
    if(step===4&&form.date&&form.date<today){setError("Choose today or a future date.");return}
    if(step===4&&form.date&&(form.start_time<"06:00"||form.start_time>"20:00")){setError("Choose a start time between 6 AM and 8 PM.");return}
    if(step===5&&form.budget_type!=="quote"&&(!form.budget||Number(form.budget)<=0)){setError("Enter a budget above zero.");return}
    if(step===7&&!form.phone.trim()){setError("Enter a phone number for job updates.");return}
    if(step<7)setStep(v=>v+1);else void submit();
  }
  function pickMedia(event:ChangeEvent<HTMLInputElement>){const files=Array.from(event.target.files??[]);if(files.length>5){setError("Choose up to five files.");return}setError("");setMedia(files)}
  function useGps(){if(!navigator.geolocation){setError("GPS is unavailable. Enter your location below.");return}setGpsBusy(true);setError("");navigator.geolocation.getCurrentPosition(async p=>{
    const coords=`${p.coords.latitude.toFixed(7)},${p.coords.longitude.toFixed(7)}`;
    try {const result=await api<{items:{label:string}[]}>("/v1/locations/reverse?coordinates="+encodeURIComponent(coords));const label=result.items?.[0]?.label;
      if(!label){setForm(v=>({...v,coordinates:coords,address:"",area:"",city:""}));setError("GPS captured. Enter your town, city and landmark to continue.");setGpsVerified(false);return}
      setForm(v=>({...v,coordinates:coords,address:label,area:label,city:label,region:"",district:"",town:""}));setGpsVerified(true);
    }catch{setForm(v=>({...v,coordinates:coords,address:"",area:"",city:""}));setGpsVerified(false);setError("GPS captured. Enter your town, city and landmark to continue.")}
    finally{setGpsBusy(false)}
  },()=>{setGpsBusy(false);setError("Location permission was not granted. You can enter your town and landmark instead.")},{enableHighAccuracy:true,timeout:15000})}
  async function submit(){if(loading)return;setLoading(true);setError("");try{
    const body={service:form.service,description:form.description,address:form.address,area:form.area,city:form.city,contact_phone:form.phone,scheduled_date:form.date||undefined,time_window:form.time_window,start_time:form.date?form.start_time:undefined,budget_type:form.budget_type,budget:form.budget_type==="quote"?undefined:form.budget,coordinates:form.coordinates||undefined,artisan_id:selected||undefined};
    const result=await api<{id:string}>("/v1/bookings",{method:"POST",headers:{"Idempotency-Key":draftKey},body:JSON.stringify(body)});
    for(const file of media){const upload=new FormData();upload.append("file",file);upload.append("purpose","booking_media");upload.append("booking_id",result.id);await api("/v1/uploads",{method:"POST",body:upload})}
    if(form.drive_url.trim())await api("/v1/drive-submissions",{method:"POST",body:JSON.stringify({purpose:"supporting_document",title:`Booking ${result.id} supporting material`,url:form.drive_url.trim()})});
    sessionStorage.removeItem(draftStorage);sessionStorage.removeItem(requestStorage);router.replace(`/bookings/${result.id}`);
  }catch(e){setError(e instanceof Error?e.message:"Could not submit the request. Please try again.")}finally{setLoading(false)}}

  return <main className="hw-app-booking"><div className="hw-app-flow-shell">
    <header className="hw-app-flow-head"><button type="button" aria-label="Previous step" onClick={()=>{if(step===0)router.push("/dashboard");else setStep(v=>v-1)}}>Back</button><strong>{steps[step]}</strong><span>{step+1} / 8</span></header>
    <div className="hw-app-progress" aria-label={`Step ${step+1} of 8`}><span style={{width:`${(step+1)/8*100}%`}}/></div>
    <div className="hw-app-flow-body"><p className="hw-app-eyebrow">{steps[step]} · Step {step+1}</p>
      {step===0&&<><h1>What do you need done?</h1><p>Choose a specific service or trade.</p><input type="search" aria-label="Search services" placeholder="AC repair, CCTV, cleaning..." value={serviceSearch} onChange={e=>{setServiceSearch(e.target.value);setLimit(24)}}/><label>Category<select value={category} onChange={e=>{setCategory(e.target.value);setLimit(24)}}><option value="">Choose category</option>{[...new Set(catalogue.map(row=>row.category))].map(name=><option key={name}>{name}</option>)}</select></label>{form.service&&<p role="status">Selected: {form.service}</p>}{(category||serviceSearch.trim())&&<><div className="hw-app-services">{serviceOptions.slice(0,limit).map(name=><button type="button" key={name} className={form.service===name?"chosen":""} onClick={()=>{update("service",name);setError("");setStep(1)}}>{name}<span aria-hidden="true">{form.service===name?"✓":""}</span></button>)}</div>{serviceOptions.length>limit&&<button type="button" className="hw-app-outline" onClick={()=>setLimit(n=>n+24)}>Show more services</button>}{!serviceOptions.length&&<p>No matching services. Try another term.</p>}</>}<button type="button" className="hw-app-outline" onClick={()=>{update("service","Help me choose");setError("");setStep(1)}}>Help me choose</button></>}
      {step===1&&<><h1>Tell us about the job.</h1><p>A short description helps professionals understand the work.</p><label>Job details<textarea rows={6} value={form.description} onChange={e=>update("description",e.target.value)} placeholder="For example, my kitchen sink is leaking and the tap needs replacing."/></label></>}
      {step===2&&<><h1>Add photos or a video.</h1><p>Optional, but useful for accurate estimates.</p><label className="hw-app-upload">Photos or short video<input type="file" multiple accept="image/jpeg,image/png,image/webp,video/mp4" onChange={pickMedia}/><span>{media.length?`${media.length} attachment(s) selected` : "Up to five JPG, PNG, WebP photos or MP4 clips"}</span></label><small>Files are uploaded when you confirm the job. Reselect them if the app refreshes.</small><label>Or add a Google Drive link (optional)<input type="url" placeholder="https://drive.google.com/..." value={form.drive_url} onChange={e=>update("drive_url",e.target.value)}/></label><small>Shared Drive links are reviewed separately; they are not automatically added to the booking gallery.</small></>}
      {step===3&&<><h1>Where is the job?</h1><p>Choose a location or enter your nearest landmark.</p><button type="button" className={`hw-app-outline ${(gpsVerified||Boolean(form.coordinates&&form.address&&form.city&&form.area))?"hw-app-gps-success":""}`} onClick={useGps} disabled={gpsBusy} aria-live="polite">{gpsBusy?"Finding your location…":(gpsVerified||Boolean(form.coordinates&&form.address&&form.city&&form.area))?"GPS location selected ✓":"Use my current location"}</button>{(gpsVerified||Boolean(form.coordinates&&form.address&&form.city&&form.area))&&<button type="button" className="hw-app-location-edit" onClick={()=>{setGpsVerified(false);setForm(v=>({...v,coordinates:"",area:"",address:"",city:""}))}}>Change location manually</button>}
        {!(gpsVerified||Boolean(form.coordinates&&form.address&&form.city&&form.area))&&<><label>Region<select value={form.region} onChange={e=>{setForm(v=>({...v,region:e.target.value,district:"",town:"",city:"",area:""}))}}><option value="">Choose region</option>{regions.map(r=><option key={r.name}>{r.name}</option>)}</select></label>
        <label>District<select value={form.district} onChange={e=>{setForm(v=>({...v,district:e.target.value,town:""}))}}><option value="">Choose district (optional)</option>{region?.districts.map(d=><option key={d.name}>{d.name}</option>)}</select></label>
        <label>Town<select value={form.town} onChange={e=>setForm(v=>({...v,town:e.target.value,area:e.target.value||v.area}))}><option value="">Choose town (optional)</option>{district?.towns.map(t=><option key={t.name}>{t.name}</option>)}</select></label>
        <label>Town or area<input value={form.area} onChange={e=>update("area",e.target.value)} placeholder="e.g. East Legon"/></label><label>Street or nearest landmark<input value={form.address} onChange={e=>update("address",e.target.value)} placeholder="e.g. Near the community library"/></label>
        <label>City<input value={form.city} onChange={e=>update("city",e.target.value)} placeholder="e.g. Accra"/></label><small>Can’t find your community? Just type your town or nearest landmark.</small></>}</>}
      {step===4&&<><h1>When do you need it?</h1><p>Choose a date for now or schedule for later.</p><div className="hw-app-choice"><button type="button" className={!form.date?"chosen":""} onClick={()=>{update("date","");setError("");setStep(5)}}>As soon as possible</button><button type="button" className={form.date?"chosen":""} onClick={()=>update("date",today)}>Schedule for later</button></div>{form.date&&<label>Preferred date<input type="date" min={today} value={form.date} onChange={e=>update("date",e.target.value)}/></label>}{form.date&&<label>Start time (6:00 AM – 8:00 PM)<input type="time" min="06:00" max="20:00" step="1800" value={form.start_time} onChange={e=>update("start_time",e.target.value)}/></label>}</>}
      {step===5&&<><h1>Set your budget.</h1><p>Choose an estimate if you’re unsure about the cost.</p><div className="hw-app-choice">{[["quote","Get an estimate"],["fixed","Fixed budget"],["hourly","Hourly"]].map(([v,label])=><button type="button" key={v} className={form.budget_type===v?"chosen":""} onClick={()=>{update("budget_type",v);if(v==="quote"){setError("");setStep(6)}}}>{label}</button>)}</div>{form.budget_type!=="quote"&&<label>Budget (GHS)<input inputMode="decimal" type="number" min="1" value={form.budget} onChange={e=>update("budget",e.target.value)} placeholder="Enter amount"/></label>}<small>No payment is taken when you submit this request.</small></>}
      {step===6&&<><h1>Available professionals.</h1><p>Choose a match or save your request while you find someone.</p>{matching?<p role="status">Finding approved, available professionals…</p>:<>{matchingError&&<p role="status">{matchingError}</p>}{matches.map(person=><button className={`hw-app-match ${selected===person.id?"chosen":""}`} type="button" key={person.id} onClick={()=>{setSelected(person.id);setStep(7)}}><span><b>{person.display_name}</b><small>{[person.trade,person.area,person.city].filter(Boolean).join(" · ")}</small></span><span aria-hidden="true">{selected===person.id?"✓":""}</span></button>)}{!matches.length&&<p>No eligible professional matched your details yet. You can still create an unassigned request and follow it in My jobs.</p>}<button type="button" className={`hw-app-match ${!selected?"chosen":""}`} onClick={()=>{setSelected("");setStep(7)}}>Save request without choosing a professional</button></>}</>}
      {step===7&&<><h1>Review your request.</h1><p>Confirm the details before submitting.</p><dl className="hw-app-review"><dt>Service</dt><dd>{form.service}</dd><dt>Details</dt><dd>{form.description}</dd><dt>Location</dt><dd>{form.address}, {location}</dd><dt>When</dt><dd>{form.date?`${form.date} · ${form.start_time}`:"As soon as possible"}</dd><dt>Budget</dt><dd>{form.budget_type==="quote"?"Request an estimate":`GHS ${form.budget} (${form.budget_type})`}</dd><dt>Professional</dt><dd>{matches.find(p=>p.id===selected)?.display_name||"Not yet selected"}</dd><dt>Attachments</dt><dd>{media.length} file(s)</dd></dl><label>Phone for job updates<input type="tel" value={form.phone} onChange={e=>update("phone",e.target.value)}/></label><small>The request will appear in My jobs. You’ll review quotes and payment details before paying.</small></>}
      {error&&<p className="hw-app-error" role="alert">{error}</p>}
    </div><footer className="hw-app-flow-actions">{step>0&&<button type="button" className="hw-app-outline" onClick={()=>{setError("");setStep(s=>s-1)}} disabled={loading}>Back</button>}<button type="button" className="hw-app-primary" onClick={next} disabled={loading||matching}>{loading?"Submitting…":step===7?"Confirm request":step===2?"Continue · photos optional":step===6?"Review request":"Continue"}</button></footer>
  </div></main>;
}
