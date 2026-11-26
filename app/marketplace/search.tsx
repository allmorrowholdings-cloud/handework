"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { LocationSearch } from "../components/location-search";
import { LocationMap } from "../components/location-map";
import { api } from "../../lib/api";

type Artisan = {
  id: string;
  display_name: string;
  trade: string;
  rating: number | null;
  review_count: number;
  distance_km: number | null;
  starting_price: number | null;
  currency: string;
  verified: boolean;
  avatar_url?: string;
  latitude?: number | null;
  longitude?: number | null;
};

type SearchResult = {
  search: { path: string; attempt: number };
  items: Artisan[];
  status: "ready" | "offline";
  located?: boolean;
};

function requestedDate(value: string) {
  if (value !== "today" && value !== "tomorrow") return "";
  const date = new Date();
  if (value === "tomorrow") date.setDate(date.getDate() + 1);
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, "0"), String(date.getDate()).padStart(2, "0")].join("-");
}

export function MarketplaceSearch() {
  const params = useSearchParams();
  const service = params.get("service") ?? "";
  const coordinates = params.get("coordinates") ?? "";
  const location = params.get("location") ?? "";
  const [attempt, setAttempt] = useState(0);
  const [when, setWhen] = useState("any");
  const [distance, setDistance] = useState("25");
  const [minRating, setMinRating] = useState(false);
  const [sort, setSort] = useState("nearest");

  const [result, setResult] = useState<SearchResult | null>(null);

  const search = useMemo(() => {
    const query = new URLSearchParams({ service, distance_km: distance });
    if (coordinates) query.set("coordinates", coordinates);
    else if (location) query.set("location", location);
    const date = requestedDate(when);
    if (date) query.set("date", date);
    return { path: `/v1/artisans/search?${query}`, attempt };
  }, [service, coordinates, location, distance, when, attempt]);

  useEffect(() => {
    const controller = new AbortController();
    api<{ items?: Artisan[]; meta?: { coordinates_used: boolean } }>(search.path, { signal: controller.signal })
      .then(body => {
        if (!controller.signal.aborted) {
          setResult({ search, items: body.items ?? [], located: body.meta?.coordinates_used, status: "ready" });
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setResult({ search, items: [], status: "offline" });
      });
    return () => controller.abort();
  }, [search]);

  const current = result?.search === search ? result : null;
  const loading = !current;
  const visible = useMemo(() => {
    const items = current?.items ?? [];
    const filtered = minRating ? items.filter(item => (item.rating ?? 0) >= 4) : [...items];
    filtered.sort(sort === "rating"
      ? (a, b) => (b.rating ?? 0) - (a.rating ?? 0)
      : sort === "match"
        ? (a, b) => b.review_count - a.review_count
        : (a, b) => (a.distance_km ?? Infinity) - (b.distance_km ?? Infinity));
    return filtered;
  }, [current, minRating, sort]);

  const bookingQuery = new URLSearchParams();
  if (service) bookingQuery.set("service", service);
  if (coordinates) bookingQuery.set("coordinates", coordinates);
  if (location) bookingQuery.set("area", location);
  const bookingHref = `/bookings/new${bookingQuery.toString() ? `?${bookingQuery}` : ""}`;


  const activeFilterCount = Number(when !== "any") + Number(distance !== "25") + Number(minRating);

  function reset() {
    setWhen("any"); setDistance("25"); setMinRating(false); setSort("nearest");
  }

  return <>
    <section className="market-head">
      <div className="shell market-head-inner">

        <h1>Find skilled hands near you.</h1>
        <p className="market-lede">Search by skill and location, then explore available professionals. Or describe the job and request help.</p>
        <LocationSearch key={params.toString()} compact initialService={service} initialLocation={location} initialCoordinates={coordinates}/>
      </div>
    </section>

    <div className="marketplace-content shell">
      <div className="market-intro-bar">
        <div><h2>Explore professionals</h2></div>
        <Link href={bookingHref} className="market-describe-link">Describe your job</Link>
      </div>

      <div className="market-layout market-layout-refined">
        <aside className="market-filter-column" aria-label="Professional search filters">
          <details className="market-filter-drawer" open>
            <summary><span>Refine results {activeFilterCount > 0 ? `(${activeFilterCount})` : ""}</span><span className="market-filter-chevron" aria-hidden="true">+</span></summary>
            <div className="filters market-filters">
              <div className="filter-title"><b>Filters</b><button type="button" onClick={reset}>Reset all</button></div>
              <label>Availability
                <select value={when} onChange={event => setWhen(event.target.value)}>
                  <option value="any">Any available time</option><option value="today">Today</option><option value="tomorrow">Tomorrow</option>
                </select>
              </label>
              <label>Distance
                <select value={distance} onChange={event => setDistance(event.target.value)}>
                  <option value="3">Within 3 km</option><option value="10">Within 10 km</option><option value="25">Within 25 km</option>
                </select>
              </label>
              <fieldset className="market-trust-filters">
                <legend>Trust</legend>
                <label className="check"><input type="checkbox" checked readOnly disabled /> Verified profiles</label>
                <label className="check"><input type="checkbox" checked={minRating} onChange={event => setMinRating(event.target.checked)} /> 4 stars and above</label>
              </fieldset>
              <p className="filter-note">Confirm prices and materials with the professional before booking.</p>
            </div>
          </details>
        </aside>

        <div className="results market-results" aria-live="polite">
          <div className="results-head">
            <div>
              <b>{service ? `Professionals for ${service}` : "Available professionals"}</b>
              <span>{loading ? "Searching..." : current?.status === "offline" ? "Search connection unavailable" : `${visible.length} matching ${visible.length === 1 ? "professional" : "professionals"}`}</span>
            </div>
            <label className="market-sort-label">Sort by
              <select aria-label="Sort professionals" className="sort-button" value={sort} onChange={event => setSort(event.target.value)}>
                <option value="nearest">Nearest first</option><option value="match">Most established</option><option value="rating">Highest rated</option>
              </select>
            </label>
          </div>

          {loading && <div className="result-state market-state"><span className="spinner" aria-hidden="true"/><h2>Checking professional availability</h2><p>Searching by your selected service, location and filters.</p></div>}

          {!loading && current?.status === "offline" && <div className="result-state market-state">
            <div className="market-state-symbol" aria-hidden="true">!</div>
            <h2>Search is temporarily unavailable</h2>
            <p>Your search details are saved here. Try again, or describe your job directly.</p>
            <div className="search-recovery">
              <button type="button" className="button button-orange" onClick={() => setAttempt(value => value + 1)}>Try again</button>
              <Link className="button market-outlined-action" href={bookingHref}>Describe your job</Link>
            </div>
          </div>}

          {!loading && current?.status === "ready" && visible.length === 0 && <div className="result-state market-state">
            <div className="market-state-symbol" aria-hidden="true">⌕</div>
            <h2>{minRating && current.items.length ? "No profiles meet this review filter" : service ? "No available match yet" : "No professionals available yet"}</h2>
            <p>{minRating && current.items.length ? "Try removing the rating filter to see more professionals." : "You can describe your job now or adjust the service, location or distance to widen your search."}</p>
            <div className="search-recovery">
              <Link className="button button-orange" href={bookingHref}>Describe your job</Link>
              {minRating ? <button className="button market-outlined-action" type="button" onClick={() => setMinRating(false)}>Clear rating filter</button>
                : distance !== "25" ? <button className="button market-outlined-action" type="button" onClick={() => setDistance("25")}>Widen to 25 km</button>
                  : <Link className="button market-outlined-action" href="/marketplace">Start a new search</Link>}
            </div>
          </div>}

          {!loading && current?.status === "ready" && visible.length > 0 && <>
            <div className="artisan-results">
              {visible.map(item => <article className="artisan-result" key={item.id}>
                <div className="artisan-avatar">{item.avatar_url ? <Image src={item.avatar_url} alt="" width={64} height={64} unoptimized/> : item.display_name.slice(0,1)}</div>
                <div className="artisan-details">
                  <div className="result-title"><h2>{item.display_name}</h2>{item.verified && <span>Verified</span>}</div>
                  <p>{item.trade}</p>
                  <small>{current.located && item.distance_km != null ? `${item.distance_km.toFixed(1)} km away` : "Distance unavailable"} · {item.review_count > 0 ? `${item.rating?.toFixed(1) ?? "–"} from ${item.review_count} reviews` : "New on handEwork"}</small>
                </div>
                <div className="result-price">{item.starting_price != null ? <><span>From</span><b>{item.currency} {item.starting_price.toLocaleString()}</b></> : <span>Quote required</span>}
                  <Link href={`/artisans/${item.id}`}>View profile</Link>
                </div>
              </article>)}
            </div>

          </>}
        </div>
        <aside className="market-map-sidebar" aria-label="Search location map">
          <div className="market-map-sidebar-heading">
            <h2>Location map</h2>
            <p>Explore the selected area. Professional pins appear only when locations are available.</p>
          </div>
          <div className="market-map-frame">
            <LocationMap items={visible} coordinates={coordinates} />
          </div>

        </aside>      </div>
    </div>
  </>;
}
