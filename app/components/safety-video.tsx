"use client";

import { useEffect, useRef, useState } from "react";

/** Keep the original video on Canva. Only create its iframe once the
 *  section is visible; remove it when the section leaves view so it stops.
 *  Canva and the browser control whether autoplay is permitted. */
export function SafetyVideo() {
  const section = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = section.current;
    if (!node) return;
    if (!("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(
      ([entry]) => setVisible(entry.isIntersecting && entry.intersectionRatio >= 0.3),
      { threshold: [0, 0.3, 0.65] }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="home-safety-video" ref={section}>
      {visible ? (
        <iframe
          src="https://www.canva.com/design/DAHb9Ap4-yw/ihwbUlvlby3reXo9-PZEkg/watch?embed"
          title="handEwork Safety and Trust"
          allow="autoplay; fullscreen"
          allowFullScreen
          referrerPolicy="strict-origin-when-cross-origin"
        />
      ) : (
        <div className="home-safety-video-idle" role="status">
          <span className="home-safety-video-play" aria-hidden="true">&#9654;</span>
          <span>Safety and trust: video available when in view</span>
        </div>
      )}
    </div>
  );
}