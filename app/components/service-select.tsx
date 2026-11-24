"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { serviceNames } from "../../lib/services";

export function ServiceSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const [extra, setExtra] = useState<string[]>([]);
  useEffect(() => {
    const controller = new AbortController();
    api<{items: string[]}>("/v1/services", {signal: controller.signal})
      .then(result => setExtra(result.items)).catch(() => {});
    return () => controller.abort();
  }, []);
  const options = new Map<string,string>();
  for (const name of [...serviceNames, ...extra, value].filter(Boolean)) {
    if (!options.has(name.toLowerCase()) || name === value) options.set(name.toLowerCase(), name);
  }
  return <select required value={value} onChange={event => onChange(event.target.value)}>
    <option value="">Choose a service</option>
    {[...options.values()].sort((a,b) => a.localeCompare(b)).map(name => <option key={name}>{name}</option>)}
  </select>;
}
