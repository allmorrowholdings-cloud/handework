"use client";

import { useEffect, useRef, useState } from "react";
import Script from "next/script";

type GoogleResponse = { credential?: string };
type GIS = { accounts: { id: { initialize: (options: { client_id: string; callback: (r: GoogleResponse) => void; auto_select: boolean }) => void; renderButton: (element: HTMLElement, options: Record<string, string | number>) => void } } };
declare global { interface Window { google?: GIS } }

export function GoogleButton({ onCredential, label = "continue_with" }: { onCredential: (credential: string) => void; label?: "signin_with" | "signup_with" | "continue_with" }) {
  const container = useRef<HTMLDivElement>(null);
  const callback = useRef(onCredential);
  const [loaded, setLoaded] = useState(false);
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
  useEffect(() => { callback.current = onCredential; }, [onCredential]);
  useEffect(() => {
    if (!loaded || !clientId || !container.current || !window.google) return;
    window.google.accounts.id.initialize({ client_id: clientId, callback: (r) => { if (r.credential) callback.current(r.credential); }, auto_select: false });
    container.current.replaceChildren();
    window.google.accounts.id.renderButton(container.current, { type: "standard", theme: "outline", size: "large", text: label, width: Math.min(320, container.current.clientWidth || 320) });
  }, [loaded, clientId, label]);
  if (!clientId) return null;
  return <div className="hw-google-auth" aria-label="Google account authentication">
    <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" onReady={() => setLoaded(true)} />
    <div ref={container} />
  </div>;
}
