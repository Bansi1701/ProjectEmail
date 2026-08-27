import type { NextConfig } from "next";

/**
 * Two build targets.
 *
 *   (default)            → `standalone`, the server bundle the Docker runner stage serves.
 *   BUILD_TARGET=pages   → `export`, flat static files for GitHub Pages.
 *
 * The Pages build is a preview of the static surface only. It cannot run the inbox —
 * that needs FastAPI, Redis and an SMTP listener. Anything server-rendered or
 * dynamic will be missing from it by definition.
 */
const isPagesBuild = process.env.BUILD_TARGET === "pages";

// GitHub project sites are served from https://<user>.github.io/<repo>/, so every
// asset and route needs that prefix. A custom domain would set this back to "".
const basePath = isPagesBuild ? "/ProjectEmail" : "";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: isPagesBuild ? "export" : "standalone",
  basePath,
  assetPrefix: basePath || undefined,
  // Pages has no image optimizer — it is a static file host.
  images: { unoptimized: isPagesBuild },
  // Emits about/index.html rather than about.html, so paths resolve without a server.
  trailingSlash: isPagesBuild,
};

export default nextConfig;
