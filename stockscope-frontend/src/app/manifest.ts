import type { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: '/',
    name: 'StockScope — Stock Research',
    short_name: 'StockScope',
    description: 'Company financials, news and SEC filings.',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    background_color: '#111513',
    theme_color: '#111513',
    lang: 'en',
    icons: [
      { src: '/pwa-assets/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/pwa-assets/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
      { src: '/pwa-assets/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  }
}
