import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import ClientLayout from "@/components/ClientLayout";

const inter = Inter({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const jetbrains = JetBrains_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Rolio — Your Career, Intelligently Matched",
  description: "AI-powered job discovery, matching, and application management. Stop searching. Start matching.",
  keywords: ["job search", "AI career", "job matching", "resume builder", "career platform", "job board"],
  authors: [{ name: "Rolio" }],
  openGraph: {
    title: "Rolio — Stop Searching. Start Matching.",
    description: "AI-powered job discovery that matches you with opportunities that actually fit — then explains exactly why.",
    type: "website",
    siteName: "Rolio",
  },
  twitter: {
    card: "summary_large_image",
    title: "Rolio — AI Career Platform",
    description: "Stop searching. Start matching. AI-powered job discovery.",
  },
  icons: {
    icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎯</text></svg>",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrains.variable}`}>
      <body className="min-h-screen antialiased">
        <a href="#main-content" className="skip-to-content">Skip to content</a>
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  );
}
