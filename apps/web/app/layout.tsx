import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "AGAS",
  description: "Adaptive, evidence-grounded general athleticism",
  applicationName: "AGAS",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  themeColor: "#15362d",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

