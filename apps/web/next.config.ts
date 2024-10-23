import type { NextConfig } from "next";

const BACKEND = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/engine/:path*", destination: `${BACKEND}/engine/:path*` },
      { source: "/synthea/:path*", destination: `${BACKEND}/synthea/:path*` },
      { source: "/analyze-meal",  destination: `${BACKEND}/analyze-meal` },
      { source: "/image-analyze/:path*", destination: `${BACKEND}/image-analyze/:path*` },
      { source: "/recommendations", destination: `${BACKEND}/recommendations` },
      { source: "/health",        destination: `${BACKEND}/health` },
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

// TODO: refactor this component

// Updated: 2023-05-29
// TODO: refactor this component
// Updated: 2023-11-12
// TODO: refactor this component