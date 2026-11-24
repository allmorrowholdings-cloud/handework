"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../lib/api";

type Professional = {id: string; display_name: string; trade: string; area?: string; city?: string};
export function Professionals() {
  const [rows, setRows] = useState<Professional[] | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    api<{items: Professional[]}>("/v1/artisans/search", {signal: controller.signal})
      .then(data => setRows(data.items.slice(0, 4)))
      .catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, []);
  return <section className="shell professional-index"><h2>Available professionals</h2>
    {rows?.length ? <ul>{rows.map(person => <li key={person.id}><Link href={`/artisans/${person.id}`}><strong>{person.display_name}</strong><span>{[person.trade,person.area,person.city].filter(Boolean).join(", ")}</span></Link></li>)}</ul> :
      <p role="status">{failed ? "Professional availability could not load." : rows ? "There are no available verified professionals to show right now." : "Checking availability..."}</p>}
    <Link className="text-link" href="/marketplace">Browse by service or area</Link>
  </section>;
}
