This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## iPhone and PWA behavior

The production app supports Add to Home Screen with a standalone manifest and Apple touch icon. Serve it over HTTPS (localhost also works for development). Service workers register only with `npm run build && npm start`, after the initial page has loaded.

Below 1024px, the authenticated app uses a `100dvh` frame: the header and bottom navigation occupy their own space and only `main` scrolls. This clips table/list content above the navigation instead of relying on iOS to paint a fixed footer over a scrolling document. Safe-area padding belongs to the header and navigation; do not add the navigation height to main's padding. Keep article/list panels in the main scroll flow. Desktop and the sign-in page retain document scrolling. Dialogs still use Headless UI's portal, focus trap and scroll locking, which make the app frame inert while open. Responsive Tailwind utilities appear after custom CSS in the production stylesheet; shell spacing uses higher specificity where it must override them.

Mobile Back/Forward restores the main scroll position for each history entry, including repeated visits to the same page. Positions stay in memory for the current sign-in and reset on a full reload. Restoration waits for loading content to grow and yields when the user interacts; same-page filter/tab changes retain their position. Keep main positioned relatively so absolute screen-reader labels cannot enlarge the root document's scroll area. Deferred panels observe main on mobile and the viewport on desktop.

Price ranges are cached in memory and stale active queries refresh on return to the app. Deeper company panels load near the viewport. The worker caches only `/offline.html`; research, API responses, sessions, and application pages are not stored by it. A network connection is required to open new research. Authentication storage is unchanged. Worker updates wait for existing app windows to close; increment the offline-cache version in `public/sw.js` when changing the fallback.

Before releasing mobile changes, check the production build at 320px, 390px, landscape/tablet widths below 1024px, and desktop. Verify the bottom bar while scrolling to the footer, menu open/close and focus restoration, browser Back/Forward, watchlist and skip-content anchors, input focus, horizontal tables, chart range changes, and news filters. Main must end at the navigation's top edge and the mobile document must not scroll. On a physical iPhone, test both Safari (with its toolbar expanded and collapsed) and Home Screen launch: no row text should appear beneath the dock during scrolling or after keyboard dismissal, rotation or return from background. Also verify notch/home-indicator spacing. Desktop viewport emulation cannot validate iOS's native toolbar and keyboard behavior. For offline fallback testing, load and reload the app online first so the worker controls the page, then disconnect and reload; retry after reconnecting.

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
