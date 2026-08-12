import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("http://localhost:3000"),
  title: "Helix — Bioinformatics Agent",
  description: "A human-controlled visual workspace for genomic quality checks.",
  openGraph: {
    title: "Helix — Bioinformatics Agent",
    description: "From raw reads to a human decision.",
    images: [{ url: "/og.png", width: 1680, height: 945 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Helix — Bioinformatics Agent",
    description: "From raw reads to a human decision.",
    images: ["/og.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
