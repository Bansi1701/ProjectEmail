import type { Metadata, Viewport } from "next";
import "./globals.css";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://bansi1701.github.io/ProjectEmail/";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  applicationName: "ProjectEmail",
  title: {
    default: "ProjectEmail — Private temporary email in one click",
    template: "%s · ProjectEmail",
  },
  description:
    "Create a temporary inbound-only inbox in one click. Receive verification codes without creating an account.",
  openGraph: {
    type: "website",
    siteName: "ProjectEmail",
    url: siteUrl,
    title: "Private email in one click",
    description:
      "Create a temporary inbound-only inbox and receive verification codes without an account.",
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0f172a",
  colorScheme: "light",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
