"use client";

import { useEffect, useRef, useState } from "react";

export function DemoVideo() {
  const ref = useRef<HTMLVideoElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const video = ref.current;
    if (!video) return;

    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    );

    let disposed = false;

    async function startPlayback(element: HTMLVideoElement) {
      if (disposed || reducedMotion.matches || !element.paused) return;

      try {
        element.muted = false;
        await element.play();
      } catch {
        if (disposed) return;

        // Browsers may require muted autoplay.
        element.muted = true;

        try {
          await element.play();
        } catch {
          // Native controls allow manual playback.
        }
      }
    }

    const start = () => {
      void startPlayback(video);
    };

    const stop = () => {
      video.pause();
    };

    if (!("IntersectionObserver" in window)) {
      start();
      return () => {
        disposed = true;
        stop();
      };
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) start();
        else stop();
      },
      { threshold: 0.25 }
    );

    observer.observe(video);

    return () => {
      disposed = true;
      observer.disconnect();
      stop();
    };
  }, []);

  return (
    <figure className="demo-video">
      <video
        ref={ref}
        src="/allmorrow-demo.mp4"
        aria-label="handEwork demonstration"
        playsInline
        controls
        preload="metadata"
        width={1080}
        height={1732}
        onError={() => setFailed(true)}
      />

      {failed && (
        <p role="status">Video unavailable right now.</p>
      )}
    </figure>
  );
}