import type { NextConfig } from "next";

/**
 * Two build targets.
 *
 *   (default)            → `standalone`, the server bundle the Docker runner stage serves.
 *   BUILD_TARGET=pages   → `export`, flat static files for GitHub Pages.
 *
 * The Pages build serves the static shell and client-side inbox. FastAPI and the
 * inbound Email Worker remain separate deployables; no server-rendered route may be
 * required for the core browser experience.
 */
const isPagesBuild = process.env.BUILD_TARGET === "pages";

// GitHub project sites are served from https://<user>.github.io/<repo>/, so every
// asset and route needs that prefix. A custom domain would set this back to "".
const basePath = isPagesBuild ? "/ProjectEmail" : "";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Keep Next's dependency tracing inside this package. The development machine has
  // an unrelated lockfile above the repository, which must not redefine our root.
  outputFileTracingRoot: process.cwd(),
  output: isPagesBuild ? "export" : "standalone",
  basePath,
  assetPrefix: basePath || undefined,
  // Pages has no image optimizer — it is a static file host.
  images: { unoptimized: isPagesBuild },
  // Emits about/index.html rather than about.html, so paths resolve without a server.
  trailingSlash: isPagesBuild,
};

export default nextConfig;
