"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Panel, StatCard } from "../../components/Charts";
import { RankedMatchList, type RankedJob } from "../../components/RankedMatchList";
import { apiGet, apiPost, loadProfile, type CandidateProfile } from "../../lib/api";
import { ENGINEERING_CATEGORIES, canonicalEngineeringCategory } from "../../lib/categories";
import { useDebouncedValue } from "../../lib/useDebouncedValue";

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

type MatchResponse = {
  disclaimer?: string;
  keyword: RankedJob[];
  semantic: RankedJob[];
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
  const router = useRouter();
  const pathname = usePathname();
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const [forYou, setForYou] = useState(false);
  const [data, setData] = useState<JobsResponse | null>(null);
  const [totalInternships, setTotalInternships] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [match, setMatch] = useState<MatchResponse | null>(null);
  const [matchBusy, setMatchBusy] = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);
  const debouncedQ = useDebouncedValue(q, 300);

  useEffect(() => {
    setProfile(loadProfile());
  }, []);

  useEffect(() => {
    const cat =
      canonicalEngineeringCategory(searchParams.get("category") || "") ||
      (searchParams.get("category") === "Other" ? "Other" : "");
    setCategory(cat);
    setForYou(searchParams.get("forYou") === "1");
  }, [searchParams]);

  function replaceFilters(next: { category?: string; forYou?: boolean }) {
    const cat = next.category !== undefined ? next.category : category;
    const fy = next.forYou !== undefined ? next.forYou : forYou;
    const params = new URLSearchParams();
    if (cat) params.set("category", cat);
    if (fy) params.set("forYou", "1");
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  useEffect(() => {
    apiGet<Overview>("/api/market/overview")
      .then((o) => setTotalInternships(o.internship_count ?? null))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (forYou) {
      setLoading(false);
      return;
    }
    const params = new URLSearchParams({
      page: String(page),
      page_size: "20",
      internship: "true",
    });
    if (debouncedQ.trim()) params.set("q", debouncedQ.trim());
    if (category) params.set("category", category);
    const ac = new AbortController();
    setError(null);
    setLoading(true);
    apiGet<JobsResponse>(`/api/jobs?${params.toString()}`, { signal: ac.signal })
      .then(setData)
      .catch((e) => {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : "Failed to load internships");
      })
      .finally(() => {
        if (!ac.signal.aborted) setLoading(false);
      });
    return () => ac.abort();
  }, [debouncedQ, category, page, forYou]);

  useEffect(() => {
    if (!forYou) {
      setMatch(null);
      setMatchError(null);
      return;
    }
    if (!profile?.skills?.length) {
      setMatch(null);
      return;
    }
    const ac = new AbortController();
    setMatchBusy(true);
    setMatchError(null);
    apiPost<MatchResponse>(
      "/api/match",
      {
        candidate: {
          skills: profile.skills,
          education_level: profile.education_level,
          education_fields: profile.education_fields,
          experience_level: profile.experience_level,
          languages: profile.languages,
          projects: profile.projects,
          target_categories: profile.target_categories,
          summary: profile.summary,
          internship_mentions: profile.internship_mentions,
        },
        method: "both",
        limit: 24,
        category: category || undefined,
        internship: true,
      },
      { signal: ac.signal }
    )
      .then(setMatch)
      .catch((e) => {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setMatchError(e instanceof Error ? e.message : "Matching failed");
        setMatch(null);
      })
      .finally(() => {
        if (!ac.signal.aborted) setMatchBusy(false);
      });
    return () => ac.abort();
  }, [forYou, profile, category]);

  function setCategoryAndUrl(next: string) {
    setPage(1);
    replaceFilters({ category: next });
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-4xl text-cedar">Internships</h1>
        <p className="mt-2 text-ink/65">
          Engineering internships from the Lebanese job boards in this dataset — focused on
          students and early-career engineers.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className={`rounded-lg px-3 py-1.5 text-sm ${
            !forYou ? "bg-cedar text-cream" : "border border-cedar/20 bg-cream text-ink/70"
          }`}
          onClick={() => {
            setPage(1);
            replaceFilters({ forYou: false });
          }}
        >
          Browse
        </button>
        <button
          type="button"
          className={`rounded-lg px-3 py-1.5 text-sm ${
            forYou ? "bg-cedar text-cream" : "border border-cedar/20 bg-cream text-ink/70"
          }`}
          onClick={() => replaceFilters({ forYou: true })}
        >
          For you
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <StatCard label="Internships in dataset" value={totalInternships ?? "—"} />
        <StatCard label="Matching filters" value={loading ? "…" : (data?.total ?? "—")} />
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {!forYou ? (
          <input
            className="rounded-lg border border-cedar/20 bg-cream px-3 py-2 text-sm md:col-span-2"
            placeholder="Search title, company…"
            value={q}
            onChange={(e) => {
              setPage(1);
              setQ(e.target.value);
            }}
          />
        ) : (
          <div className="md:col-span-2" />
        )}
        <select
          className="rounded-lg border border-cedar/20 bg-cream px-3 py-2 text-sm"
          value={category}
          onChange={(e) => setCategoryAndUrl(e.target.value)}
        >
          {ENG_CATEGORIES.map((c) => (
            <option key={c || "all"} value={c}>
              {c || "All categories"}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="text-sm text-cedar">{error}</p>}

      {forYou ? (
        <div className="space-y-4">
          {!profile?.skills?.length ? (
            <Panel title="No CV loaded">
              <p className="text-sm text-ink/70">
                Upload a CV first so ranking uses your skills, not an empty profile.
              </p>
              <Link
                href="/cv"
                className="mt-3 inline-block rounded-lg bg-cedar px-4 py-2 text-sm text-cream hover:opacity-90"
              >
                Go to CV Analyzer
              </Link>
            </Panel>
          ) : (
            <>
              {matchBusy && <p className="text-sm text-ink/50">Ranking internships for your CV…</p>}
              {matchError && <p className="text-sm text-cedar">{matchError}</p>}
              {match && !matchBusy && (
                <>
                  <div className="grid gap-6 lg:grid-cols-2">
                    <RankedMatchList title="Keyword match" jobs={match.keyword || []} />
                    <RankedMatchList title="Semantic match" jobs={match.semantic || []} />
                  </div>
                  {match.disclaimer ? (
                    <p className="text-xs text-ink/50">{match.disclaimer}</p>
                  ) : null}
                </>
              )}
            </>
          )}
        </div>
      ) : (
        <>
      {loading && <p className="text-sm text-ink/50">Loading internships…</p>}

      <div className="space-y-3">
        {!loading && (data?.jobs || []).length === 0 && !error ? (
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
        </>
      )}
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
