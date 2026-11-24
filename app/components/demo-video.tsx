"use client";

import { useEffect, useRef } from "react";

export function DemoVideo() {
  const ref = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const video = ref.current;
    if (!video || !("IntersectionObserver" in window)) return;
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.intersectionRatio < 0.25) video.pause();
      else if (!motion.matches) void video.play().catch(() => {});
    }, { threshold: [0, 0.25] });
    observer.observe(video);
    return () => observer.disconnect();
  }, []);
  return <figure className="demo-video"><video
    ref={ref}
    src="/allmorrow-demo.mp4"
    aria-label="Allmorrow demo"
    muted
    playsInline
    controls
    preload="metadata"
  /></figure>;
}
