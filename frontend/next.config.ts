import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Bundle only what the server needs into .next/standalone: the Docker image runs
  // `node server.js` without node_modules, which keeps it small.
  output: "standalone",
};

export default nextConfig;
