import type { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: '/',
    name: 'StockScope — Stock Research',
    short_name: 'StockScope',
    description: 'Your workspace for company fundamentals and source-backed research.',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    background_color: '#101218',
    theme_color: '#101218',
    lang: 'en',
    icons: [
      { src: '/pwa-assets/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/pwa-assets/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
      { src: '/pwa-assets/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  }
}
