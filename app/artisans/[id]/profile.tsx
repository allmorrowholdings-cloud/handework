"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { api } from "../../../lib/api";

type Artisan = { id:string; display_name:string; trade:string; bio?:string; city?:string; area?:string; years_experience?:number; rating:number|null; review_count:number; starting_price:number|null; currency:string; verified:boolean; instant_booking:boolean; avatar_url?:string; };
type Portfolio = { id:string; title:string; description?:string; service:string; media_url:string; media_type:string; before_after?:string };
type WorkProof = { score:number; verified_jobs:number; completion_rate:number; average_rating:number|null; repeat_clients:number; years_verified:number; unresolved_disputes:number; disclaimer:string };

export function PublicArtisanProfile({ id }: { id: string }) {
  const [record, setRecord] = useState<{artisan:Artisan;portfolio:Portfolio[];workproof:WorkProof}|null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => { api<{artisan:Artisan;portfolio:Portfolio[];workproof:WorkProof}>(`/v1/artisans/${id}`).then(setRecord).catch(() => setFailed(true)); }, [id]);
  if (failed) return <section className="section shell"><div className="result-state"><h2>Profile unavailable</h2><p>This profile could not be opened. Return to search to find another artisan.</p><Link className="button button-dark" href="/marketplace">Back to search</Link></div></section>;
  if (!record) return <section className="section shell"><div className="loading-line"><span />Loading verified profile…</div></section>;
  const { artisan, portfolio, workproof } = record;
  return <>
    <section className="artisan-profile-hero"><div className="shell artisan-profile-intro"><div className="public-avatar">{artisan.avatar_url ? <Image src={artisan.avatar_url} alt="" width={150} height={150} unoptimized /> : artisan.display_name.slice(0,1)}</div><div><h1>{artisan.display_name}</h1><p>{artisan.trade} · {[artisan.area,artisan.city].filter(Boolean).join(", ") || "Service location set in app"}</p></div><Link className="button button-orange" href={`/bookings/new?artisan=${artisan.id}&instant=${artisan.instant_booking?"1":"0"}`}>{artisan.instant_booking?"Book or request quote":"Request this artisan"}</Link></div></section>
    <section className="section shell artisan-profile-grid"><article><h2>Work you can check before you book.</h2><p>{artisan.bio || "This artisan has not added a public biography yet."}</p><dl><div><dt>Experience</dt><dd>{artisan.years_experience ? `${artisan.years_experience} years` : "Not stated"}</dd></div><div><dt>Reviews</dt><dd>{artisan.review_count ? `${artisan.rating?.toFixed(1)} from ${artisan.review_count}` : "New on handEwork"}</dd></div><div><dt>Starting price</dt><dd>{artisan.starting_price ? `${artisan.currency} ${artisan.starting_price.toLocaleString()}` : "Quote required"}</dd></div></dl></article><aside><p>Agree the scope and price in handEwork. Authorize payment only inside the booking. Release follows completed-work approval or an administered dispute decision.</p><Link className="text-link" href="/safety">Read the safety standard</Link></aside></section>
    <section className="section shell workproof-public"><div><h2>Your skills travel with you. Your work history proves them.</h2><p>Verified economic activity and actual work history—including independently checked work completed outside handEwork.</p><small>{workproof.disclaimer}</small></div><div className="workproof-score"><span>WorkProof score</span><strong>{workproof.score}</strong><small>out of 1,000</small></div><dl><div><dt>Verified jobs</dt><dd>{workproof.verified_jobs}</dd></div><div><dt>Completion</dt><dd>{workproof.completion_rate.toFixed(0)}%</dd></div><div><dt>Client rating</dt><dd>{workproof.average_rating?.toFixed(1) || "—"}</dd></div><div><dt>Repeat clients</dt><dd>{workproof.repeat_clients}</dd></div><div><dt>Verified activity</dt><dd>{workproof.years_verified.toFixed(1)} years</dd></div><div><dt>Open disputes</dt><dd>{workproof.unresolved_disputes}</dd></div></dl></section>
    <section className="section portfolio-public shell"><div className="section-head"><div><h2>Proof of work.</h2></div></div>{portfolio.length ? <div className="portfolio-grid">{portfolio.map((item) => <article key={item.id}>{item.media_type === "image" && <Image src={item.media_url} alt={item.title} width={620} height={420} unoptimized />}<div><span>{item.service}</span><h3>{item.title}</h3>{item.description && <p>{item.description}</p>}</div></article>)}</div> : <div className="result-state"><span className="state-mark">⌁</span><h2>No approved portfolio item yet</h2><p>Only reviewed, live uploads appear here.</p></div>}</section>
  </>;
}
