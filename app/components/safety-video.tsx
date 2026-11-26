"use client";

import { useEffect, useRef, useState } from "react";

const videoUrl = "https://www.canva.com/design/DAHb9Ap4-yw/ihwbUlvlby3reXo9-PZEkg/watch?embed";


export function SafetyVideo() {
  const target = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const element = target.current;
    if (!element) return;
    if (!("IntersectionObserver" in window)) { setVisible(true); return; }
    const observer = new IntersectionObserver(([entry]) => setVisible(entry.intersectionRatio >= 0.3), {threshold:[0,0.3,0.65]});
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return <div className="home-safety-video" ref={target}>
    {visible && <iframe
      loading="eager"
      src={videoUrl}
      title="handEwork safety and trust film"
      allow="autoplay; fullscreen; encrypted-media"
      allowFullScreen
      referrerPolicy="strict-origin-when-cross-origin"
    />}

  </div>;
}
