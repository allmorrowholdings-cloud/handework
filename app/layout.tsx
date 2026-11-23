import type { Metadata } from "next";
import "./globals.css";
import "mapbox-gl/dist/mapbox-gl.css";

export const metadata: Metadata = {
  title: { default: "handEwork | Get it done with skilled hands.", template: "%s | handEwork" },
  description: "Get it done with skilled hands. Find trusted artisans near you, book work clearly and pay safely with handEwork.",
  applicationName: "handEwork",
  manifest: "/manifest.webmanifest",
  openGraph: {
    title: "handEwork | Get it done with skilled hands.",
    description: "Get it done with skilled hands. Find trusted artisans near you, book work clearly and pay safely with handEwork.",
    siteName: "handEwork",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "handEwork | Get it done with skilled hands.",
    description: "Get it done with skilled hands. Find trusted artisans near you, book work clearly and pay safely with handEwork.",
  },
  icons: {
    icon: [{ url: "/favicon.png", type: "image/png", sizes: "512x512" }],
    shortcut: "/favicon.png",
    apple: "/pwa-icon-192.png",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" data-theme="dark" suppressHydrationWarning><body>{children}</body></html>;
}
