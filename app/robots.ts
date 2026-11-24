import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {rules:{userAgent:"*", allow:["/", "/artisan/pro$"], disallow:["/admin", "/auth/", "/artisan/", "/bookings/", "/bookings$", "/my-jobs", "/wallet", "/dashboard", "/messages", "/notifications", "/settings", "/disputes", "/referrals"]}, sitemap:"https://handework.allmorrow.com/sitemap.xml"};
}
