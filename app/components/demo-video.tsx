"use client";

import { useEffect, useRef, useState } from "react";

export function DemoVideo() {
  const ref = useRef<HTMLVideoElement>(null);
  const [failed, setFailed] = useState(false);
  const [soundRequired, setSoundRequired] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const video = element;

    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    );

    let disposed = false;

    async function start() {
      if (reducedMotion.matches || disposed || !video.paused) return;

      try {
        video.muted = false;
        await video.play();
        if (!disposed) setSoundRequired(false);
      } catch {
        if (disposed) return;

        video.muted = true;

        try {
          await video.play();
          if (!disposed) setSoundRequired(true);
        } catch {
          if (!disposed) setSoundRequired(true);
        }
      }
    }

    if (!("IntersectionObserver" in window)) {
      void start();
      return () => {
        disposed = true;
        video.pause();
      };
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          void start();
        } else {
          video.pause();
        }
      },
      { threshold: 0.25 }
    );

    observer.observe(video);

    return () => {
      disposed = true;
      observer.disconnect();
      video.pause();
    };
  }, []);

  function enableSound() {
    const video = ref.current;
    if (!video) return;

    video.muted = false;
    video.volume = 1;

    void video.play()
      .then(() => setSoundRequired(false))
      .catch(() => setSoundRequired(true));
  }

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

      {soundRequired && !failed && (
        <button
          type="button"
          className="video-enable-sound"
          onClick={enableSound}
        >
          Enable sound
        </button>
      )}

      {failed && (
        <a href="https://www.canva.com/design/DAHbz7MtI7w/0LwZPGWkqQzkCKqdJnDWXw/watch">
          Watch the demonstration on Canva
        </a>
      )}
    </figure>
  );
}
