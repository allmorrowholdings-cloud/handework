"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../lib/api";
import { EmptyState } from "./app-shell";

type Item = Record<string, unknown>;
type DisplayVariant = "default" | "admin" | "training";

export function LiveRecords({
  endpoint,
  emptyTitle,
  emptyText,
  action,
  variant = "default",
  linkBase,
}: {
  endpoint: string;
  emptyTitle: string;
  emptyText: string;
  action?: { href: string; label: string };
  variant?: DisplayVariant;
  linkBase?: string;
}) {
  const [result, setResult] = useState<{ endpoint: string; items: Item[] | null } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    api<{ items: Item[] }>(endpoint, { signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setResult({endpoint, items: data.items ?? []}); })
      .catch(() => { if (!controller.signal.aborted) setResult({endpoint, items: null}); });
    return () => controller.abort();
  }, [endpoint]);

  const items = result?.items;
  if (result?.endpoint !== endpoint) return <div className="loading-line"><span />Loading current records…</div>;
  if (!items) return <EmptyState title="Unable to load this information" text="Please try again in a moment." />;
  if (!items.length) return <EmptyState title={emptyTitle} text={emptyText} action={action ? <Link className="button button-dark" href={action.href}>{action.label}</Link> : undefined} />;

  function destination(item: Item) {
    if (endpoint === "/v1/bookings") return `${linkBase ?? "/bookings"}/${String(item.id)}`;
    if (endpoint === "/v1/conversations") return `${linkBase ?? "/messages"}/${String(item.id)}`;
    return null;
  }

  function content(item: Item) {
    if (variant === "admin") {
      return <div><b>{String(item.title ?? item.reference ?? item.reason ?? item.kind ?? "Operational record")}</b><span>{String(item.status ?? item.decision ?? item.created_at ?? "").replaceAll("_", " ")}</span></div>;
    }
    if (variant === "training") {
      return <div><b>{String(item.title ?? "Training opportunity")}</b><span>{[item.provider, item.trade, item.city ?? item.delivery_mode].filter(Boolean).map(String).join(" · ")}</span></div>;
    }
    return <div><b>{String(item.service ?? item.title ?? item.name ?? item.reference ?? "Work record")}</b><span>{[item.reference, typeof item.status === "string" ? item.status.replaceAll("_", " ") : item.created_at].filter(Boolean).map(String).join(" · ")}</span></div>;
  }

  return <div className="record-list hw-premium-records">{items.map((item, index) => {
    const href = destination(item);
    return <div className="record-row" key={String(item.id ?? index)}>{content(item)}{href && <Link href={href}>Open</Link>}{typeof item.evidence_url === "string" && <a href={item.evidence_url} target="_blank" rel="noreferrer">Review evidence</a>}</div>;
  })}</div>;
}
