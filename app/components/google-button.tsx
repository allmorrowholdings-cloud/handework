"use client";

import { useEffect, useRef, useState } from "react";
import Script from "next/script";

type GoogleResponse = { credential?: string };
type GIS = { accounts: { id: {
  initialize: (options: { client_id: string; callback: (r: GoogleResponse) => void; auto_select: boolean }) => void;
  renderButton: (element: HTMLElement, options: Record<string, string | number>) => void;
} } };
declare global { interface Window { google?: GIS } }

export function GoogleButton({ onCredential, label = "continue_with" }: {
  onCredential: (credential: string) => void;
  label?: "signin_with" | "signup_with" | "continue_with";
}) {
  const container = useRef<HTMLDivElement>(null);
  const callback = useRef(onCredential);
  const [loaded, setLoaded] = useState(false);
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  useEffect(() => { callback.current = onCredential; }, [onCredential]);

  useEffect(() => {
    if (!loaded || !clientId || !container.current || !window.google) return;
    const element = container.current;
    const google = window.google;
    google.accounts.id.initialize({
      client_id: clientId,
      callback: response => { if (response.credential) callback.current(response.credential); },
      auto_select: false,
    });
    let previousWidth = 0;
    const render = () => {
      const available = element.parentElement?.clientWidth || element.clientWidth;
      if (available < 180) return;
      const width = Math.max(180, Math.min(400, Math.floor(available)));
      if (width === previousWidth && element.firstElementChild) return;
      previousWidth = width;
      element.replaceChildren();
      google.accounts.id.renderButton(element, {
        type: "standard", theme: "outline", size: "large", shape: "pill",
        text: label, width, logo_alignment: "left",
      });
    };
    const resizeObserver = new ResizeObserver(render);
    if (element.parentElement) resizeObserver.observe(element.parentElement);
    render();
    return () => resizeObserver.disconnect();
  }, [loaded, clientId, label]);

  if (!clientId) return null;
  return <div className="hw-google-auth" aria-label="Continue with Google">
    <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" onReady={() => setLoaded(true)} />
    <div className="hw-google-container" ref={container} />
  </div>;
}
