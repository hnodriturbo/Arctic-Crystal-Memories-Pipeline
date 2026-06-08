// next.config.mjs
// Next.js 16 configuration for K9 Crystal Pipeline web app.

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactCompiler: true,

  // Allow serving pipeline images from the API route without Next.js image optimization
  // (images are served raw via /api/image/[...] route handler)

  // Disable x-powered-by header
  poweredByHeader: false,
};

export default nextConfig;
