"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/market", label: "Eng. Market" },
  { href: "/jobs", label: "Eng. Jobs" },
  { href: "/internships", label: "Internships" },
  { href: "/companies", label: "Companies" },
  { href: "/cv", label: "CV Analyzer" },
  { href: "/skill-gap", label: "Skill Gap" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <header className="border-b border-cedar/20 bg-cream/90 backdrop-blur sticky top-0 z-40">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
        <Link href="/" className="font-display text-xl tracking-tight text-cedar">
          Lebanon CareerAI
        </Link>
        <nav className="flex flex-wrap gap-1 text-sm">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-md px-2.5 py-1.5 transition ${
                  active
                    ? "bg-cedar text-cream"
                    : "text-ink/70 hover:bg-sand hover:text-ink"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}

export function Disclaimer() {
  return (
    <footer className="mt-16 border-t border-cedar/15 bg-sand/40">
      <div className="mx-auto max-w-6xl px-4 py-6 text-xs leading-relaxed text-ink/60">
        <p>
          Skill-gap recommendations are analytical estimates based on this engineering-focused
          dataset of publicly accessible Lebanese engineering jobs and internships collected during
          the project&apos;s data-collection period — not the entire Lebanese job market. CV files
          are processed ephemerally and are not permanently stored by default.
        </p>
      </div>
    </footer>
  );
}
