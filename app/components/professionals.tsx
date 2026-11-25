"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../lib/api";

type Professional = {id:string;display_name:string;trade:string;area?:string;city?:string};
export function Professionals() {
  const [rows,setRows] = useState<Professional[]>([]);
  useEffect(() => {
    const controller = new AbortController();
    api<{items:Professional[]}>("/v1/artisans/search",{signal:controller.signal})
      .then(data => { if (!controller.signal.aborted) setRows(data.items.slice(0,4)); })
      .catch(() => { if (!controller.signal.aborted) setRows([]); });
    return () => controller.abort();
  },[]);
  if (!rows.length) return null;
  return <section className="shell professional-index"><h2>Available professionals</h2>
    <ul>{rows.map(person => <li key={person.id}><Link href={`/artisans/${person.id}`}><strong>{person.display_name}</strong><span>{[person.trade,person.area,person.city].filter(Boolean).join(", ")}</span></Link></li>)}</ul>
    <Link className="text-link" href="/marketplace">Browse by service or area</Link>
  </section>;
}