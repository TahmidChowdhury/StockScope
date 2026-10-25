import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "@/components/Providers";
import { PwaRegistration } from "@/components/PwaRegistration";

export const metadata: Metadata = {
  title: "StockScope — Stock Research",
  description:
    "Company fundamentals, dated news research, and links to original SEC filings",
  applicationName: "StockScope",
  appleWebApp: {
    capable: true,
    title: "StockScope",
    statusBarStyle: "black",
  },
  icons: {
    icon: [{ url: "/pwa-assets/icon.svg", type: "image/svg+xml" }],
    apple: [{ url: "/pwa-assets/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#101218",
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <PwaRegistration />
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
