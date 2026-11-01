/** @type {import('next').NextConfig} */
const nextConfig = {
  devIndicators: process.env.NEXT_PUBLIC_SHOW_DEVTOOLS === 'true' ? { position: 'top-left' } : false,
  async headers() {
    return [
      {
        source: '/sw.js',
        headers: [
          { key: 'Content-Type', value: 'application/javascript; charset=utf-8' },
          { key: 'Cache-Control', value: 'no-cache, no-store, must-revalidate' },
          { key: 'Service-Worker-Allowed', value: '/' },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
