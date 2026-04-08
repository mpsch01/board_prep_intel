import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Netlify adapter handles edge runtime automatically.
  // Images from Supabase Storage
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "*.supabase.co",
        pathname: "/storage/v1/object/public/**",
      },
    ],
  },
  // Sanity Studio embedded at /admin/studio
  // served as a client-only page — no SSR needed
};

export default nextConfig;
