import type { NextConfig } from "next";

const BACKEND = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

// Static demo for GitHub Pages (pnpm build:demo): no API server. lib/api.ts answers from
// captured fixtures, so rewrites, headers, and the server-side route handler are left out.
// Excluding the "ts" page extension drops app/api/**/route.ts; pages and layouts are .tsx.
const DEMO = process.env.NEXT_PUBLIC_DEMO === "1";
const DEMO_BASE_PATH = process.env.DEMO_BASE_PATH ?? "/demos/nutri-node";

const demoConfig: NextConfig = {
  output: "export",
  basePath: DEMO_BASE_PATH,
  trailingSlash: true,
  images: { unoptimized: true },
  pageExtensions: ["tsx"],
};

const nextConfig: NextConfig = DEMO ? demoConfig : {
  output: "standalone",
  async rewrites() {
    return [
      { source: "/engine/:path*", destination: `${BACKEND}/engine/:path*` },
      { source: "/synthea/:path*", destination: `${BACKEND}/synthea/:path*` },
      { source: "/analyze-meal",  destination: `${BACKEND}/analyze-meal` },
      { source: "/image-analyze/:path*", destination: `${BACKEND}/image-analyze/:path*` },
      { source: "/recommendations", destination: `${BACKEND}/recommendations` },
      { source: "/health",        destination: `${BACKEND}/health` },
      { source: "/api/metrics",   destination: `${BACKEND}/api/metrics` },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: https:",
              "font-src 'self'",
              "connect-src 'self'",
              "frame-src 'none'",
              "object-src 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

export default nextConfig;


