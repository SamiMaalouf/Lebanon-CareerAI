"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Panel, StatCard } from "../../components/Charts";
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
  education_level?: string | null;
  experience_level?: string | null;
  skills?: { name: string; is_required: boolean }[];
};

type JobsResponse = {
  total: number;
  page: number;
  page_size: number;
  jobs: JobRow[];
};

type Overview = {
  internship_count?: number;
};

const STUDENT_FRIENDLY = new Set(["Bachelor's", "Internship", "Entry-level", "0-2 years"]);

function EligibilityPills({
  education,
  experience,
}: {
  education?: string | null;
  experience?: string | null;
}) {
  const values = [education, experience].filter((v): v is string => Boolean(v && v.trim()));
  if (!values.length) return null;
  return (
    <>
      {values.map((value, i) => {
        const friendly = STUDENT_FRIENDLY.has(value);
        return (
          <span
            key={`${i}-${value}`}
            className={`rounded-full px-2 py-0.5 text-xs ${
              friendly ? "bg-sea/15 text-sea" : "bg-sand text-ink/60"
            }`}
          >
            {value}
          </span>
        );
      })}
    </>
  );
}

function InternshipsPageInner() {
  const searchParams = useSearchParams();
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<JobsResponse | null>(null);
  const [totalInternships, setTotalInternships] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const cat = searchParams.get("category") || "";
    if (cat) setCategory(cat);
  }, [searchParams]);

  useEffect(() => {
    apiGet<Overview>("/api/market/overview")
      .then((o) => setTotalInternships(o.internship_count ?? null))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: "20",
      internship: "true",
    });
    if (q.trim()) params.set("q", q.trim());
    if (category) params.set("category", category);
    setError(null);
    apiGet<JobsResponse>(`/api/jobs?${params.toString()}`)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [q, category, page]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-4xl text-cedar">Internships</h1>
        <p className="mt-2 text-ink/65">
          Engineering internships from the Lebanese job boards in this dataset — focused on
          students and early-career engineers.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <StatCard label="Internships in dataset" value={totalInternships ?? "—"} />
        <StatCard label="Matching filters" value={data?.total ?? "—"} />
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <input
          className="rounded-lg border border-cedar/20 bg-cream px-3 py-2 text-sm md:col-span-2"
          placeholder="Search title, company…"
          value={q}
          onChange={(e) => {
            setPage(1);
            setQ(e.target.value);
          }}
        />
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

      <div className="space-y-3">
        {(data?.jobs || []).length === 0 && !error ? (
          <Panel title="No internships found">
            <p className="text-sm text-ink/55">
              Try another category, or clear the search. This dataset currently has a small
              internship pool.
            </p>
          </Panel>
        ) : null}
        {(data?.jobs || []).map((job) => (
          <div
            key={job.job_id}
            className="rounded-xl border border-cedar/15 bg-cream/80 p-4"
          >
            <div className="flex flex-wrap items-center gap-2">
              <div className="font-medium text-ink">{job.title}</div>
              <span className="rounded-full bg-sea/15 px-2 py-0.5 text-xs text-sea">
                Internship
              </span>
              <EligibilityPills
                education={job.education_level}
                experience={job.experience_level === "Internship" ? null : job.experience_level}
              />
            </div>
            <div className="mt-1 text-sm text-ink/60">
              {[job.company, job.location, job.category, job.source].filter(Boolean).join(" · ")}
            </div>
            {(job.skills || []).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {(job.skills || []).slice(0, 8).map((s) => (
                  <span key={s.name} className="rounded-md bg-sand px-2 py-0.5 text-xs">
                    {s.name}
                  </span>
                ))}
              </div>
            )}
            {job.source_url ? (
              <a
                className="mt-2 inline-block text-sm text-sea underline"
                href={job.source_url}
                target="_blank"
                rel="noreferrer"
              >
                Open original posting
              </a>
            ) : null}
          </div>
        ))}
      </div>

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
  );
}

export default function InternshipsPage() {
  return (
    <Suspense fallback={<p className="text-ink/60">Loading internships…</p>}>
      <InternshipsPageInner />
    </Suspense>
  );
}
