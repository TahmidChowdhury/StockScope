/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    // Ensure TypeScript path mapping works correctly
    typedRoutes: false,
  },
  // Ensure module resolution works properly
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': new URL('./src', import.meta.url).pathname,
    };
    return config;
  },
};

module.exports = nextConfig;