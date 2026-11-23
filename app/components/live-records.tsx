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
  const [items, setItems] = useState<Item[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    setState("loading");
    api<{ items: Item[] }>(endpoint)
      .then((data) => {
        setItems(data.items ?? []);
        setState("ready");
      })
      .catch(() => setState("error"));
  }, [endpoint]);

  if (state === "loading") return <div className="loading-line"><span />Loading current records…</div>;
  if (state === "error") return <EmptyState title="Connect the handEwork API" text="This page is ready for live data and will not use sample records while the backend is unavailable." />;
  if (!items.length) return <EmptyState title={emptyTitle} text={emptyText} action={action ? <Link className="button button-dark" href={action.href}>{action.label}</Link> : undefined} />;

  function destination(item: Item) {
    if (endpoint === "/v1/bookings") return `${linkBase ?? "/bookings"}/${String(item.id)}`;
    if (endpoint === "/v1/conversations") return `${linkBase ?? "/messages"}/${String(item.id)}`;
    return null;
  }

  function content(item: Item) {
    if (variant === "admin") {
      return <div><b>{String(item.title ?? item.reference ?? item.reason ?? item.kind ?? "Operational record")}</b><span>{String(item.status ?? item.decision ?? item.created_at ?? "")}</span></div>;
    }
    if (variant === "training") {
      return <div><b>{String(item.title ?? "Training opportunity")}</b><span>{[item.provider, item.trade, item.city ?? item.delivery_mode].filter(Boolean).map(String).join(" · ")}</span></div>;
    }
    return <div><b>{String(item.title ?? item.name ?? item.reference ?? "Record")}</b><span>{String(item.status ?? item.created_at ?? "")}</span></div>;
  }

  return <div className="record-list">{items.map((item, index) => {
    const href = destination(item);
    return <div className="record-row" key={String(item.id ?? index)}>{content(item)}{href && <Link href={href}>Open</Link>}</div>;
  })}</div>;
}
