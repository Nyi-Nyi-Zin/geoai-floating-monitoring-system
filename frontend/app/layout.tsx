import type { Metadata } from "next";
import AppProviders from "./components/app-providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "DeltaWatch | Maubin Flood Terrain",
  description:
    "Human-supervised flood terrain and drainage decision support for Maubin Township.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
