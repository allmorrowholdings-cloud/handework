"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { LocationSearch } from "../components/location-search";
import { MapboxMap } from "./mapbox-map";
import { api } from "../../lib/api";

type Artisan={id:string;display_name:string;trade:string;rating:number|null;review_count:number;distance_km:number;starting_price:number|null;currency:string;verified:boolean;avatar_url?:string;latitude?:number|null;longitude?:number|null};
function requestedDate(value:string){const result=new Date();if(value==="tomorrow")result.setDate(result.getDate()+1);if(value==="week")return "";return value==="today"||value==="tomorrow"?result.toISOString().slice(0,10):""}

export function MarketplaceSearch(){
  const params = useSearchParams();
  const service = params.get("service") ?? "";
  const coordinates = params.get("coordinates") ?? "";
  const location = params.get("location") ?? "";
  const [attempt, setAttempt] = useState(0);
  const [when, setWhen] = useState("any");
  const [distance, setDistance] = useState("10");
  const [minRating, setMinRating] = useState(false);
  const [sort, setSort] = useState("nearest");

  const search = useMemo(() => {
    if (!service) return null;
    const query = new URLSearchParams({ service, distance_km: distance });
    if (coordinates) query.set("coordinates", coordinates);
    else if (location) query.set("location", location);
    const date = requestedDate(when);
    if (date) query.set("date", date);
    return { path: `/v1/artisans/search?${query}`, attempt };
  }, [service, coordinates, location, distance, when, attempt]);

  const [result, setResult] = useState<{
    search: NonNullable<typeof search>;
    items: Artisan[];
    status: "ready" | "offline";
  } | null>(null);

  useEffect(() => {
    if (!search) return;
    const controller = new AbortController();

    api<{ items?: Artisan[] }>(search.path, { signal: controller.signal })
      .then((body) => {
        if (!controller.signal.aborted) setResult({ search, items: body.items ?? [], status: "ready" });
      })
      .catch(() => {
        if (!controller.signal.aborted) setResult({ search, items: [], status: "offline" });
      });

    return () => controller.abort();
  }, [search]);

  const currentResult = result?.search === search ? result : null;
  const loading = Boolean(search && !currentResult);
  const status = currentResult?.status ?? (search ? "idle" : "ready");
  const visible = useMemo(() => {
    const items = currentResult?.items ?? [];
    const rows = minRating ? items.filter((item) => (item.rating ?? 0) >= 4) : [...items];
    rows.sort(sort === "rating" ? (a, b) => (b.rating ?? 0) - (a.rating ?? 0) :
      sort === "match" ? (a, b) => b.review_count - a.review_count :
      (a, b) => a.distance_km - b.distance_km);
    return rows;
  }, [currentResult, minRating, sort]);

  const bookingQuery = new URLSearchParams({ service });
  if (coordinates) bookingQuery.set("coordinates", coordinates);
  if (location) bookingQuery.set("area", location);

  function reset(){setWhen("any");setDistance("10");setMinRating(false);setSort("nearest")}
  return <><section className="market-head"><div className="shell"><h1>Find skilled hands near you.</h1><LocationSearch key={params.toString()} compact initialService={service} initialLocation={location} initialCoordinates={coordinates}/></div></section><section className={`market-layout shell${process.env.NEXT_PUBLIC_MAPBOX_TOKEN ? "" : " results-only"}`}><aside className="filters"><div className="filter-title"><b>Filter</b><button type="button" onClick={reset}>Reset</button></div><label>When<select value={when} onChange={(event)=>setWhen(event.target.value)}><option value="any">Any available time</option><option value="today">Today</option><option value="tomorrow">Tomorrow</option></select></label><label>Distance<select value={distance} onChange={(event)=>setDistance(event.target.value)}><option value="3">Within 3 km</option><option value="10">Within 10 km</option><option value="25">Within 25 km</option></select></label><div>Trust<label className="check"><input type="checkbox" checked disabled/> Verified only</label><label className="check"><input type="checkbox" checked={minRating} onChange={(event)=>setMinRating(event.target.checked)}/> 4 stars and above</label></div><p className="filter-note">Confirm the price and materials with your artisan before booking.</p></aside><div className="results"><div className="results-head"><div>{service && <Link className="text-link" href={`/bookings/new?${bookingQuery}`}>Describe this job</Link>}<b>{service?`Results for “${service}”`:"Start a search"}</b><span>{visible.length?`${visible.length} artisans found`:"Live availability appears here"}</span></div><select className="sort-button" value={sort} onChange={(event)=>setSort(event.target.value)}><option value="nearest">Nearest first</option><option value="match">Most established</option><option value="rating">Highest rated</option></select></div>{loading&&<div className="result-state"><span className="spinner"/><h2>Checking nearby availability</h2><p>Distance and schedule are being calculated.</p></div>}{!loading&&status==="offline"&&<div className="result-state"><h2>Search is temporarily unavailable</h2><p>Try again without re-entering your search.</p><button type="button" className="button button-orange" onClick={()=>setAttempt((current)=>current+1)}>Try again</button></div>}{!loading&&status==="ready"&&visible.length===0&&<div className="result-state"><span className="state-mark">⌖</span><h2>{service?"No available artisan matched this search":"Tell us what needs doing"}</h2>{service ? <>
        <p>You can request a quote for this job or adjust your search.</p>
        <div className="search-recovery">
          <Link className="button button-orange" href={`/bookings/new?${bookingQuery}`}>Request this job</Link>
          {distance !== "25" && <button className="button ghost-button" type="button" onClick={() => setDistance("25")}>Widen to 25 km</button>}
        </div>
      </> : <p>Use a service and location above to check live artisan profiles.</p>}</div>}<div className="artisan-results">{visible.map((item)=><article className="artisan-result" key={item.id}><div className="artisan-avatar">{item.avatar_url?<Image src={item.avatar_url} alt="" width={56} height={56} unoptimized/>:item.display_name.slice(0,1)}</div><div><div className="result-title"><h2>{item.display_name}</h2>{item.verified&&<span>Verified</span>}</div><p>{item.trade}</p><small>{item.distance_km.toFixed(1)} km away · {item.review_count?`${item.rating?.toFixed(1)} from ${item.review_count} reviews`:"New on handEwork"}</small></div><div className="result-price">{item.starting_price?<><span>From</span><b>{item.currency} {item.starting_price.toLocaleString()}</b></>:<span>Quote required</span>}<a href={`/artisans/${item.id}`}>View profile</a></div></article>)}</div></div>{process.env.NEXT_PUBLIC_MAPBOX_TOKEN && <aside className="map-panel"><MapboxMap items={visible} coordinates={coordinates}/><p>Map pins are rounded for privacy. Search distance is calculated from GPS coordinates; route distance can be checked during booking.</p></aside>}</section></>;
}
