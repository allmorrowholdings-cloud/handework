import type { MetadataRoute } from "next";
import { serviceGuides } from "../lib/service-guides";
export default function sitemap(): MetadataRoute.Sitemap {
  return ["", "/services", ...serviceGuides.map(s=>`/services/${s.slug}`), "/how-it-works", "/safety", "/about", "/contact", "/join/artisan", "/artisan/pro", "/shop", "/training", "/support"].map(path=>({url:"https://handework.allmorrow.com"+path}));
}
