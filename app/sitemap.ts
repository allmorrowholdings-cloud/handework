import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  return ["", "/marketplace", "/how-it-works", "/safety", "/about", "/join/artisan", "/artisan/pro", "/shop", "/training", "/support"].map(path=>({url:"https://handework.allmorrow.com"+path}));
}
