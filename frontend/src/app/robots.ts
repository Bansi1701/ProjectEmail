import type { MetadataRoute } from "next";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://bansi1701.github.io/ProjectEmail/";

export const dynamic = "force-static";

export default function robots(): MetadataRoute.Robots {
  const url = new URL(siteUrl);
  const prefix = url.pathname.replace(/\/$/, "");
  const privateRoutes = ["/inbox/", "/message/", "/internal/", "/admin/"].map(
    (route) => `${prefix}${route}`,
  );

  return {
    rules: [
      { userAgent: "*", allow: `${prefix}/`, disallow: privateRoutes },
      { userAgent: "OAI-SearchBot", allow: `${prefix}/`, disallow: privateRoutes },
    ],
    sitemap: new URL("sitemap.xml", siteUrl).toString(),
  };
}
