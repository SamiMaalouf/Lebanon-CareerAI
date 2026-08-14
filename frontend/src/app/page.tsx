"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { StatCard } from "../components/Charts";
import { apiGet } from "../lib/api";

type Overview = {
  total_jobs: number;
  internship_count?: number;
  non_internship_count?: number;
  companies: number;
  sources?: { name: string; count: number }[];
  collection_window?: {
    collection_date_min?: string | null;
    collection_date_max?: string | null;
    date_posted_min?: string | null;
    date_posted_max?: string | null;
  };
  is_real_dataset?: boolean;
  dataset_note: string;
};

const ACTIONS = [
  {
    href: "/cv",
    step: "1",
    title: "Upload CV",
    body: "Parse your CV, then get Fix / Learn / Apply coaching for engineering roles.",
  },
  {
    href: "/skill-gap",
    step: "2",
    title: "Skill Gap",
    body: "Compare two career paths and see which tools Lebanese ads ask you to show.",
  },
  {
    href: "/jobs?forYou=1",
    step: "3",
    title: "Ranked jobs",
    body: "Keyword vs semantic matches for your saved CV — not just a keyword browse.",
  },
];

export default function OverviewPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Overview>("/api/market/overview")
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (error) {
    return (
      <div className="rounded-xl border border-cedar/30 bg-cream p-6">
        <h1 className="font-display text-3xl text-cedar">Lebanon CareerAI</h1>
        <p className="mt-3 text-sm text-ink/70">
          Could not reach the API. Start Postgres and the FastAPI backend, then ingest data.
        </p>
        <pre className="mt-4 overflow-auto rounded-lg bg-ink/90 p-3 text-xs text-cream">{error}</pre>
      </div>
    );
  }

  if (!data) {
    return <p className="text-ink/60">Loading market overview…</p>;
  }

  const internships = data.internship_count ?? 0;
  const engineeringJobs =
    data.non_internship_count ?? Math.max(0, data.total_jobs - internships);

  const windowLabel = [
    data.collection_window?.collection_date_min,
    data.collection_window?.collection_date_max,
  ]
    .filter(Boolean)
    .join(" → ");

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm uppercase tracking-[0.2em] text-sea">
          Lebanese engineering career intelligence
        </p>
        <h1 className="mt-2 font-display text-4xl text-cedar sm:text-5xl">Lebanon CareerAI</h1>
        <p className="mt-3 max-w-2xl text-ink/70">
          Upload your CV, see the skill gap for a target path, then ranked jobs from this Lebanese
          engineering dataset.
        </p>
        <div className="mt-4 flex flex-wrap gap-2 text-xs">
          <span
            className={`rounded-full px-3 py-1 ${
              data.is_real_dataset ? "bg-sea/15 text-sea" : "bg-cedar/15 text-cedar"
            }`}
          >
            {data.is_real_dataset ? "Real collected dataset" : "Demo / mixed dataset"}
          </span>
          <span className="rounded-full bg-sand px-3 py-1 text-ink/70">
            Engineering + internships
          </span>
          {windowLabel ? (
            <span className="rounded-full bg-sand px-3 py-1 text-ink/70">
              Collected {windowLabel}
            </span>
          ) : null}
          {data.collection_window?.date_posted_max ? (
            <span className="rounded-full bg-sand px-3 py-1 text-ink/70">
              Newest posting {data.collection_window.date_posted_max}
            </span>
          ) : null}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Engineering jobs" value={engineeringJobs} />
        <StatCard label="Internships" value={internships} />
        <StatCard label="Companies" value={data.companies} />
        <StatCard label="Sources" value={(data.sources || []).length} />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {ACTIONS.map((action) => (
          <Link
            key={action.href}
            href={action.href}
            className="rounded-2xl border border-cedar/15 bg-cream/80 p-5 shadow-sm transition hover:border-cedar/40 hover:bg-cream"
          >
            <div className="text-xs uppercase tracking-wide text-sea">Step {action.step}</div>
            <div className="mt-1 font-display text-xl text-cedar">{action.title}</div>
            <p className="mt-2 text-sm text-ink/65">{action.body}</p>
          </Link>
        ))}
      </div>

      <p className="text-sm text-ink/55">{data.dataset_note}</p>
    </div>
  );
}
