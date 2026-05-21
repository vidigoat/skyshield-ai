import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Skip linting during build (we lint separately).
  // Three.js / globe.gl / satellite.js are browser-only, marked as external.
  serverExternalPackages: ["globe.gl", "three", "satellite.js"],
};

export default nextConfig;
