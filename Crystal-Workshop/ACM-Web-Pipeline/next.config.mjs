/** @type {import('next').NextConfig} */
const nextConfig = {
  /* config options here */
  reactCompiler: true,

  /*
   * puppeteer is required at runtime only, to ask where Chromium is, and it
   * resolves that cache directory relative to its own module location. Bundled
   * into the server output it would answer from the wrong place, so it is left
   * external and loaded from node_modules the way it expects.
   */
  serverExternalPackages: ["puppeteer"],
};

export default nextConfig;
