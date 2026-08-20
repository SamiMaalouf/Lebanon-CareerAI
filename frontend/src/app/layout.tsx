import type { Metadata } from "next";
import { Disclaimer, Nav } from "../components/Nav";
import "./globals.css";

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
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Source+Sans+3:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen antialiased">
        <div className="page-shell min-h-screen">
          <Nav />
          <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
          <Disclaimer />
        </div>
      </body>
    </html>
  );
}
