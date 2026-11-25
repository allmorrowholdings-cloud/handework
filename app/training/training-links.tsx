"use client";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { DriveLinks, type DriveLink } from "../components/drive-links";

export function TrainingLinks() {
  const [items, setItems] = useState<DriveLink[]>([]);
  const [message, setMessage] = useState("Loading resources…");
  useEffect(() => {
    const controller = new AbortController();
    api<{items: DriveLink[]}>("/v1/training/drive-resources", {signal: controller.signal})
      .then(data => { setItems(data.items); setMessage("No reviewed resources yet."); })
      .catch(() => { if (!controller.signal.aborted) setMessage("Resources could not be loaded."); });
    return () => controller.abort();
  }, []);
  return items.length ? <DriveLinks items={items}/> : <p>{message}</p>;
}
