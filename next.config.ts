import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  serverExternalPackages: ['cheerio', 'better-sqlite3'],
};

export default nextConfig;
