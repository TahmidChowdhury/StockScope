This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## iPhone and PWA behavior

The production app supports Add to Home Screen with a standalone manifest and Apple touch icon. Serve it over HTTPS (localhost also works for development). Service workers register only with `npm run build && npm start`, after the initial page has loaded.

The document owns page scrolling; mobile navigation renders in a Headless UI portal so it stays attached to the viewport and becomes inert behind dialogs. Keep content clear of both navigation and iPhone safe areas using the shared shell spacing. Do not add transformed ancestors around navigation or nested vertical scrolling to mobile article/list panels. Responsive Tailwind utilities appear after custom CSS in the production stylesheet; shell padding uses higher specificity so tablet utilities cannot overwrite bottom-bar clearance.

Price ranges are cached in memory and stale active queries refresh on return to the app. Deeper company panels load near the viewport. The worker caches only `/offline.html`; research, API responses, sessions, and application pages are not stored by it. A network connection is required to open new research. Authentication storage is unchanged. Worker updates wait for existing app windows to close; increment the offline-cache version in `public/sw.js` when changing the fallback.

Before releasing mobile changes, check the production build at 320px, 390px, landscape/tablet widths below 1024px, and desktop. Verify the bottom bar while scrolling to the footer, menu open/close and focus restoration, input focus, horizontal tables, chart range changes, and news filters. On a physical iPhone, additionally verify home-screen launch, notch/home-indicator spacing, keyboard dismissal, rotation, and return from background. For offline fallback testing, load and reload the app online first so the worker controls the page, then disconnect and reload; retry after reconnecting.

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
