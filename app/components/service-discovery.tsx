"use client";
import {useState} from "react";
import Link from "next/link";
import {catalogue,findServices,serviceNames} from "../../lib/service-catalogue";

const categories=[...new Set(catalogue.map(row=>row.category))];
const featured=[{name:"Plumbing",mark:"01",image:"plumbing.webp"},{name:"Electrical",mark:"02",image:"electrical.webp"},{name:"AC repair",mark:"03"},{name:"Home cleaning",mark:"04"},{name:"CCTV installation",mark:"05"},{name:"Architectural design",mark:"06"},{name:"Carpentry",mark:"07",image:"carpentry.webp"},{name:"Solar panel installation",mark:"08"}];
export function ServiceDiscovery({installed=false}:{installed?:boolean}){
  const [query,setQuery]=useState("");
  const [category,setCategory]=useState("");
  const [showAll,setShowAll]=useState(false);
  const [limit,setLimit]=useState(24);
  const results=findServices(query).filter(name=>!category||catalogue.some(row=>row.category===category&&row.name===name));
  const browsing=showAll||Boolean(query.trim()||category);
  const book=(name:string)=>`${installed?"/app/book":"/bookings/new"}?${new URLSearchParams({service:name})}`;
  return <section className="hw-discovery" aria-label="Find a service">
    <header className="hw-discovery-heading"><span>THE RIGHT HANDS FOR THE JOB</span><h1>Get it done with skilled hands.</h1><p>From everyday fixes to specialist projects. Choose what needs doing and tell us where.</p></header>
    <div className="hw-discovery-search"><label htmlFor="hw-discovery-query">What do you need help with?</label><input id="hw-discovery-query" type="search" placeholder="Try AC repair, CCTV or cleaning" value={query} onChange={e=>{setQuery(e.target.value);setLimit(24)}}/></div>
    {!browsing&&<><div className="hw-discovery-section-head"><h2>Popular services</h2><button type="button" onClick={()=>setShowAll(true)}>See all →</button></div><div className="hw-discovery-featured">{featured.filter(item=>serviceNames.includes(item.name)).map(item=><Link key={item.name} href={book(item.name)} className="hw-discovery-tile"><span className="hw-discovery-tile-art" style={item.image?{backgroundImage:`url(/services/${item.image})`}:undefined} aria-hidden="true">{!item.image&&item.mark}</span><b>{item.name}</b><span aria-hidden="true">↗</span></Link>)}</div></>}
    <div className="hw-discovery-section-head"><h2>Explore by category</h2>{browsing&&<button type="button" onClick={()=>{setQuery("");setCategory("");setShowAll(false);setLimit(24)}}>Reset</button>}</div>
    <label className="hw-discovery-category">Service category<select value={category} onChange={e=>{setCategory(e.target.value);setShowAll(true);setLimit(24)}}><option value="">All {categories.length} categories</option>{categories.map(name=><option key={name}>{name}</option>)}</select></label>
    {!browsing&&<div className="hw-discovery-categories">{categories.slice(0,8).map(name=><button type="button" key={name} onClick={()=>{setCategory(name);setShowAll(true);setLimit(24)}}>{name}<span aria-hidden="true">→</span></button>)}</div>}
    {browsing&&<div className="hw-discovery-results"><p role="status">{results.length} matching service options</p>{results.length===0&&<p>No service found. Try another term or describe your job below.</p>}<div className="hw-discovery-list">{results.slice(0,limit).map(name=><Link key={name} href={book(name)}><span>{name}</span><span aria-hidden="true">→</span></Link>)}</div>{results.length>limit&&<button type="button" className="hw-discovery-more" onClick={()=>setLimit(n=>n+24)}>Show more services</button>}</div>}
    <div className="hw-discovery-help"><div><h2>Big project or small fix?</h2><p>Not sure which service you need? Describe the work in your own words.</p></div><Link href={book("Help me choose")}>Describe your job →</Link></div>
    <p className="hw-discovery-note">Service options are not a guarantee of local professional availability. We check eligibility and location during booking.</p>
  </section>
}
