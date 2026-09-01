import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  agentRules: false,
  // Vercel packages the application with its own Next.js adapter. The standalone
  // bundle is retained for the independently deployable Docker image.
  output: process.env.VERCEL === "1" ? undefined : "standalone",
};

export default nextConfig;
