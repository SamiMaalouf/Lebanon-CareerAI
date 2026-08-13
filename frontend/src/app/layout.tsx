import type { Metadata } from "next";
import { Fraunces, Source_Sans_3 } from "next/font/google";
import { Disclaimer, Nav } from "../components/Nav";
import "./globals.css";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
});

const sans = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Lebanon CareerAI — Engineering",
  description:
    "AI-Powered Lebanese Engineering Career & Skill Gap Analyzer — engineering jobs, internships, CV analysis, and skill-gap coaching.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${sans.variable} min-h-screen antialiased`}>
        <div className="page-shell min-h-screen">
          <Nav />
          <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
          <Disclaimer />
        </div>
      </body>
    </html>
  );
}
