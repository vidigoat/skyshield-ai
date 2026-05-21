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
  title: "SkyShield AI — Open AI agent for satellite safety",
  description:
    "Anyone with a satellite can ask 'is it safe?' in plain English. Verified physics, validated against the US Office of Space Commerce TraCSS benchmark. Built solo at 14.",
  openGraph: {
    title: "SkyShield AI",
    description: "Open AI agent for satellite safety. Verified physics, plain English.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col bg-[#0a0e27] text-slate-100">
        {children}
      </body>
    </html>
  );
}
