/**
 * GitHub Pages static export (spec §53, §54).
 *
 * - output: "export" — no Server Actions, no API routes, no SSR runtime.
 * - basePath from NEXT_PUBLIC_BASE_PATH: empty for local dev,
 *   "/V-1-science-skill" for GitHub Pages builds.
 * - trailingSlash: true (Pages-friendly).
 */

/** @type {import('next').NextConfig} */
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig = {
  output: "export",
  basePath,
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
};

export default nextConfig;
