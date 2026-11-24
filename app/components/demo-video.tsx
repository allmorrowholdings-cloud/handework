"use client";

import { useEffect, useRef, useState } from "react";

export function DemoVideo() {
  const ref = useRef<HTMLVideoElement>(null);
  const [failed, setFailed] = useState(false);
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
    preload="none"
    width={1080} height={1732} onError={() => setFailed(true)}
  />{failed && <a href="https://www.canva.com/design/DAHbz7MtI7w/0LwZPGWkqQzkCKqdJnDWXw/watch">Watch the demonstration on Canva</a>}</figure>;
}
