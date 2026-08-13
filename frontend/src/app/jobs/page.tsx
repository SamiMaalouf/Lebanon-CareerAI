"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Panel, SimpleBarChart, StatCard } from "../../components/Charts";
import { apiGet } from "../../lib/api";
import { ENGINEERING_CATEGORIES } from "../../lib/categories";

const ENG_CATEGORIES = ["", ...ENGINEERING_CATEGORIES, "Other"];

type JobRow = {
  job_id: string;
  title: string;
  company?: string;
  location?: string;
  category?: string;
  source?: string;
  source_url?: string;
  date_posted?: string;
  is_internship?: boolean;
  skills?: { name: string; is_required: boolean }[];
};

type JobsResponse = {
  total: number;
  page: number;
  page_size: number;
  jobs: JobRow[];
};

type Overview = {
  sources: { name: string; count: number }[];
  categories?: { name: string; count: number }[];
};

type CareerInsights = {
  category: string;
  job_count: number;
  top_skills: { skill: string; pct: number; count: number }[];
  education: { name: string; count: number }[];
  experience: { name: string; count: number }[];
  related_careers: { name: string; score: number }[];
};

function JobsPageInner() {
  const searchParams = useSearchParams();
  const [q, setQ] = useState("");
  const [source, setSource] = useState("");
  const [category, setCategory] = useState("");
  const [company, setCompany] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<JobsResponse | null>(null);
  const [sources, setSources] = useState<{ name: string; count: number }[]>([]);
  const [career, setCareer] = useState<CareerInsights | null>(null);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const cat = searchParams.get("category") || "";
    const co = searchParams.get("company") || "";
    if (cat) setCategory(cat);
    if (co) setCompany(co);
  }, [searchParams]);

  useEffect(() => {
    apiGet<Overview>("/api/market/overview")
      .then((o) => setSources(o.sources || []))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: "15",
      internship: "false",
    });
    if (q.trim()) params.set("q", q.trim());
    if (source) params.set("source", source);
    if (category) params.set("category", category);
    if (company.trim()) params.set("company", company.trim());
    setError(null);
    apiGet<JobsResponse>(`/api/jobs?${params.toString()}`)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [q, source, category, company, page]);

  useEffect(() => {
    if (!category || category === "Other") {
      setCareer(null);
      return;
    }
    apiGet<CareerInsights>(`/api/careers/${encodeURIComponent(category)}`)
      .then(setCareer)
      .catch(() => setCareer(null));
  }, [category]);

  async function openJob(jobId: string) {
    try {
      const detail = await apiGet<Record<string, unknown>>(`/api/jobs/${encodeURIComponent(jobId)}`);
      setSelected(detail);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load job");
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-4xl text-cedar">Engineering Jobs</h1>
        <p className="mt-2 text-ink/65">
          Browse Lebanese engineering roles. Pick a category for skill demand and career insights
          from this dataset. Looking for internships? Use the Internships page.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <input
          className="rounded-lg border border-cedar/20 bg-cream px-3 py-2 text-sm md:col-span-2"
          placeholder="Search title, company, description…"
          value={q}
          onChange={(e) => {
            setPage(1);
            setQ(e.target.value);
          }}
        />
        <select
          className="rounded-lg border border-cedar/20 bg-cream px-3 py-2 text-sm"
          value={source}
          onChange={(e) => {
            setPage(1);
            setSource(e.target.value);
          }}
        >
          <option value="">All sources</option>
          {sources.map((s) => (
            <option key={s.name} value={s.name}>
              {s.name} ({s.count})
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-cedar/20 bg-cream px-3 py-2 text-sm"
          value={category}
          onChange={(e) => {
            setPage(1);
            setCategory(e.target.value);
          }}
        >
          {ENG_CATEGORIES.map((c) => (
            <option key={c || "all"} value={c}>
              {c || "All categories"}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="text-sm text-cedar">{error}</p>}

      {company ? (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-cedar/15 bg-sand/40 px-3 py-2 text-sm">
          <span className="text-ink/70">
            Filtered by company: <span className="font-medium text-ink">{company}</span>
          </span>
          <button
            type="button"
            className="rounded-md border border-cedar/20 px-2 py-0.5 text-xs text-cedar hover:bg-cream"
            onClick={() => {
              setPage(1);
              setCompany("");
            }}
          >
            Clear
          </button>
        </div>
      ) : null}

      {career && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <h2 className="font-display text-2xl text-ink">Career insights · {career.category}</h2>
            <StatCard label="Jobs in category" value={career.job_count} />
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <Panel title="Top skills">
              <SimpleBarChart
                data={(career.top_skills || []).slice(0, 8).map((s) => ({
                  name: s.skill,
                  pct: s.pct,
                }))}
                valueKey="pct"
              />
            </Panel>
            <Panel title="Education">
              <SimpleBarChart data={(career.education || []).slice(0, 6)} />
            </Panel>
            <Panel title="Experience / related">
              <SimpleBarChart data={(career.experience || []).slice(0, 5)} />
              {(career.related_careers || []).length > 0 && (
                <ul className="mt-3 space-y-1 text-sm text-ink/70">
                  {(career.related_careers || []).slice(0, 4).map((r) => (
                    <li key={r.name} className="flex justify-between gap-2">
                      <span>{r.name}</span>
                      <span className="text-ink/45">{r.score}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3 space-y-3">
          <StatCard label="Matching jobs" value={data?.total ?? "—"} />
          {(data?.jobs || []).map((job) => (
            <button
              key={job.job_id}
              type="button"
              onClick={() => openJob(job.job_id)}
              className="w-full rounded-xl border border-cedar/15 bg-cream/80 p-4 text-left hover:border-cedar/40"
            >
              <div className="flex flex-wrap items-center gap-2">
                <div className="font-medium text-ink">{job.title}</div>
              </div>
              <div className="mt-1 text-sm text-ink/60">
                {[job.company, job.location, job.category, job.source].filter(Boolean).join(" · ")}
              </div>
            </button>
          ))}
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="rounded-lg border border-cedar/20 px-3 py-1.5 text-sm disabled:opacity-40"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={!data || page * data.page_size >= data.total}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-lg border border-cedar/20 px-3 py-1.5 text-sm disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>

        <div className="lg:col-span-2">
          <Panel title="Job detail">
            {!selected ? (
              <p className="text-sm text-ink/50">Select a posting to inspect skills and source.</p>
            ) : (
              <div className="space-y-3 text-sm">
                <h3 className="font-display text-xl text-ink">{String(selected.title)}</h3>
                <p className="text-ink/60">
                  {[selected.company, selected.location, selected.category]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
                <p>
                  Source: <span className="text-cedar">{String(selected.source)}</span>
                </p>
                {selected.source_url ? (
                  <a
                    className="text-sea underline"
                    href={String(selected.source_url)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open original posting
                  </a>
                ) : null}
                <div>
                  <div className="mb-1 font-medium">Extracted skills</div>
                  <div className="flex flex-wrap gap-2">
                    {((selected.skills as { name: string }[]) || []).map((s) => (
                      <span key={s.name} className="rounded-md bg-sand px-2 py-1 text-xs">
                        {s.name}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="max-h-64 overflow-auto whitespace-pre-wrap text-ink/70">
                  {String(selected.description || selected.cleaned_text || "").slice(0, 2500)}
                </div>
              </div>
            )}
          </Panel>
          {sources.length > 0 && (
            <div className="mt-6">
              <Panel title="Jobs by source">
                <SimpleBarChart data={sources} />
              </Panel>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function JobsPage() {
  return (
    <Suspense fallback={<p className="text-ink/60">Loading jobs…</p>}>
      <JobsPageInner />
    </Suspense>
  );
}
