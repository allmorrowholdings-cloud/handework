import { Suspense } from "react";
import type { Metadata } from "next";
import { Header } from "../components/header";
import { Footer } from "../components/footer";
import { MarketplaceSearch } from "./search";

export const metadata: Metadata = { title: "Find an artisan", description: "Search verified artisans near you by skill, distance, availability and budget." };

export default function MarketplacePage() { return <main className="paper-page marketplace-page"><Header /><Suspense fallback={<p className="shell" role="status">Loading artisan search…</p>}><MarketplaceSearch /></Suspense><Footer /></main>; }
