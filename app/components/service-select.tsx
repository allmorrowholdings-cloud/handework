"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { serviceNames, findServices } from "../../lib/service-catalogue";

export function ServiceSelect({ value, onChange, allowUnknown = false }: { allowUnknown?: boolean; value: string; onChange: (value: string) => void }) {
  const [search, setSearch] = useState("");
  const [extra, setExtra] = useState<string[]>([]);
  useEffect(() => {
    const controller = new AbortController();
    api<{items: string[]}>("/v1/services", {signal: controller.signal})
      .then(result => setExtra(result.items)).catch(() => {});
    return () => controller.abort();
  }, []);
  const options = new Map<string,string>();
  for (const name of [...(search ? findServices(search) : serviceNames), ...extra.filter(name=>!search||name.toLowerCase().includes(search.toLowerCase())), ...(allowUnknown ? ["Help me choose"] : []), value].filter(Boolean)) {
    if (!options.has(name.toLowerCase()) || name === value) options.set(name.toLowerCase(), name);
  }
  return <><input type="search" aria-label="Search services" placeholder="Search services" value={search} onChange={event=>setSearch(event.target.value)}/><select aria-label="Choose a service" required value={value} onChange={event => onChange(event.target.value)}>
    <option value="">Choose a service</option>
    {[...options.values()].sort((a,b) => a.localeCompare(b)).map(name => <option key={name}>{name}</option>)}
  </select></>;
}
