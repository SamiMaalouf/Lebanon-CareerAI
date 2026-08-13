"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Panel, StatCard } from "../../components/Charts";
import { apiGet } from "../../lib/api";

type CompanyRow = {
  company: string;
  job_count: number;
  top_categories: { name: string; count: number }[];
};

type CompaniesResponse = {
  companies: CompanyRow[];
  unnamed_job_count?: number;
  named_job_count?: number;
  total_jobs?: number;
};

export default function CompaniesPage() {
  const [rows, setRows] = useState<CompanyRow[]>([]);
  const [unnamed, setUnnamed] = useState(0);
  const [totalJobs, setTotalJobs] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    setBusy(true);
    apiGet<CompaniesResponse>("/api/market/companies?limit=100")
      .then((res) => {
        setRows(res.companies || []);
        setUnnamed(res.unnamed_job_count ?? 0);
        const named = res.named_job_count ?? (res.companies || []).reduce((s, r) => s + (r.job_count || 0), 0);
        setTotalJobs(res.total_jobs ?? named + (res.unnamed_job_count ?? 0));
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setBusy(false));
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-4xl text-cedar">Companies</h1>
        <p className="mt-2 text-ink/65">
          Employers hiring for engineering roles in this Lebanese dataset — click a company to
          browse their postings. Some boards omit the employer name.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label="Named employers" value={busy ? "…" : rows.length} />
        <StatCard label="Employer not listed" value={busy ? "…" : unnamed} />
        <StatCard label="Jobs represented" value={busy ? "…" : totalJobs} />
      </div>

      {error && <p className="text-sm text-cedar">{error}</p>}

      <Panel title="Top hiring companies">
        {busy ? (
          <p className="text-sm text-ink/50">Loading…</p>
        ) : rows.length === 0 && unnamed === 0 ? (
          <p className="text-sm text-ink/50">No companies found in the dataset yet.</p>
        ) : (
          <ul className="divide-y divide-cedar/10">
            {rows.map((row) => (
              <li key={row.company}>
                <Link
                  href={`/jobs?company=${encodeURIComponent(row.company)}`}
                  className="flex flex-col gap-2 py-3 hover:bg-sand/40 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <div className="font-medium text-ink">{row.company}</div>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {(row.top_categories || []).map((c) => (
                        <span
                          key={c.name}
                          className="rounded-md bg-sea/10 px-2 py-0.5 text-xs text-sea"
                        >
                          {c.name} ({c.count})
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="shrink-0 text-sm text-ink/55">
                    {row.job_count} job{row.job_count === 1 ? "" : "s"}
                  </div>
                </Link>
              </li>
            ))}
            {unnamed > 0 ? (
              <li className="flex flex-col gap-1 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="font-medium text-ink/70">Employer not listed</div>
                  <p className="mt-1 text-xs text-ink/50">
                    Board chrome or confidential ads — not a real company name.
                  </p>
                </div>
                <div className="shrink-0 text-sm text-ink/55">
                  {unnamed} job{unnamed === 1 ? "" : "s"}
                </div>
              </li>
            ) : null}
          </ul>
        )}
      </Panel>
    </div>
  );
}
