import type { Metadata } from "next";
import "./globals.css";
import "./public-design.css";
import "./website-growth.css";
import { ThemeInitializer } from "./components/theme-toggle";
import { SessionActivity } from "./components/session-activity";
import "maplibre-gl/dist/maplibre-gl.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://handework.allmorrow.com"),
  title: { default: "handEwork | Get it done with skilled hands.", template: "%s | handEwork" },
  description: "Get it done with skilled hands. Find trusted artisans near you, book work clearly and pay safely with handEwork.",
  applicationName: "handEwork",
  manifest: "/manifest.webmanifest",
  openGraph: {
    title: "handEwork | Get it done with skilled hands.",
    description: "Get it done with skilled hands. Find trusted artisans near you, book work clearly and pay safely with handEwork.",
    siteName: "handEwork",
    images: [{ url: "/handework-opening-poster.png", alt: "handEwork — Get it done with skilled hands." }],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    images: ["/handework-opening-poster.png"],
    title: "handEwork | Get it done with skilled hands.",
    description: "Get it done with skilled hands. Find trusted artisans near you, book work clearly and pay safely with handEwork.",
  },
  icons: {
    icon: [{ url: "/favicon.png", type: "image/png", sizes: "512x512" }],
    shortcut: "/favicon.png",
    apple: "/handework-app-icon-192.png",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" data-theme="light" suppressHydrationWarning><body><ThemeInitializer /><SessionActivity />{children}</body></html>;
}
