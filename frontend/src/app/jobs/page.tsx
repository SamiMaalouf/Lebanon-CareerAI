"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Panel, SimpleBarChart, StatCard } from "../../components/Charts";
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
};

type CareerInsights = {
  category: string;
  job_count: number;
  top_skills: { skill: string; pct: number; count: number }[];
  education: { name: string; count: number }[];
  experience: { name: string; count: number }[];
  related_careers: { name: string; score: number }[];
};

type MatchResponse = {
  disclaimer?: string;
  keyword: RankedJob[];
  semantic: RankedJob[];
};

function JobsPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const [q, setQ] = useState("");
  const [source, setSource] = useState("");
  const [category, setCategory] = useState("");
  const [company, setCompany] = useState("");
  const [skill, setSkill] = useState("");
  const [forYou, setForYou] = useState(false);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<JobsResponse | null>(null);
  const [sources, setSources] = useState<{ name: string; count: number }[]>([]);
  const [career, setCareer] = useState<CareerInsights | null>(null);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
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
    const rawCat = searchParams.get("category") || "";
    const cat = canonicalEngineeringCategory(rawCat) || (rawCat === "Other" ? "Other" : "");
    setCategory(cat);
    setCompany(searchParams.get("company") || "");
    setSkill(searchParams.get("skill") || "");
    setForYou(searchParams.get("forYou") === "1");
  }, [searchParams]);

  function replaceFilters(next: {
    category?: string;
    company?: string;
    skill?: string;
    forYou?: boolean;
  }) {
    const cat = next.category !== undefined ? next.category : category;
    const co = next.company !== undefined ? next.company : company;
    const sk = next.skill !== undefined ? next.skill : skill;
    const fy = next.forYou !== undefined ? next.forYou : forYou;
    const params = new URLSearchParams();
    if (cat) params.set("category", cat);
    if (co) params.set("company", co);
    if (sk) params.set("skill", sk);
    if (fy) params.set("forYou", "1");
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  useEffect(() => {
    apiGet<Overview>("/api/market/overview")
      .then((o) => setSources(o.sources || []))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (forYou) {
      setLoading(false);
      return;
    }
    const params = new URLSearchParams({
      page: String(page),
      page_size: "15",
      internship: "false",
    });
    if (debouncedQ.trim()) params.set("q", debouncedQ.trim());
    if (source) params.set("source", source);
    if (category) params.set("category", category);
    if (company.trim()) params.set("company", company.trim());
    if (skill.trim()) params.set("skill", skill.trim());
    const ac = new AbortController();
    setError(null);
    setLoading(true);
    apiGet<JobsResponse>(`/api/jobs?${params.toString()}`, { signal: ac.signal })
      .then(setData)
      .catch((e) => {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : "Failed to load jobs");
      })
      .finally(() => {
        if (!ac.signal.aborted) setLoading(false);
      });
    return () => ac.abort();
  }, [debouncedQ, source, category, company, skill, page, forYou]);

  useEffect(() => {
    if (forYou || !category || category === "Other") {
      setCareer(null);
      return;
    }
    apiGet<CareerInsights>(`/api/careers/${encodeURIComponent(category)}`)
      .then(setCareer)
      .catch(() => setCareer(null));
  }, [category, forYou]);

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
        internship: false,
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
          Browse Lebanese engineering roles, or rank them against your saved CV. Looking for
          internships? Use the Internships page.
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

      <div className="grid gap-3 md:grid-cols-4">
        {!forYou ? (
          <input
            className="rounded-lg border border-cedar/20 bg-cream px-3 py-2 text-sm md:col-span-2"
            placeholder="Search title, company, description…"
            value={q}
            onChange={(e) => {
              setPage(1);
              setQ(e.target.value);
            }}
          />
        ) : (
          <div className="md:col-span-2" />
        )}
        {!forYou ? (
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
        ) : (
          <div />
        )}
        <select
          className="rounded-lg border border-cedar/20 bg-cream px-3 py-2 text-sm"
          value={category}
          onChange={(e) => {
            setPage(1);
            replaceFilters({ category: e.target.value });
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
              replaceFilters({ company: "" });
            }}
          >
            Clear
          </button>
        </div>
      ) : null}

      {skill ? (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-cedar/15 bg-sand/40 px-3 py-2 text-sm">
          <span className="text-ink/70">
            Filtered by skill: <span className="font-medium text-ink">{skill}</span>
          </span>
          <button
            type="button"
            className="rounded-md border border-cedar/20 px-2 py-0.5 text-xs text-cedar hover:bg-cream"
            onClick={() => {
              setPage(1);
              replaceFilters({ skill: "" });
            }}
          >
            Clear
          </button>
        </div>
      ) : null}

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
              {matchBusy && <p className="text-sm text-ink/50">Ranking jobs for your CV…</p>}
              {matchError && <p className="text-sm text-cedar">{matchError}</p>}
              {match && !matchBusy && (
                <>
                  <div className="grid gap-6 lg:grid-cols-2">
                    <RankedMatchList
                      title="Keyword match"
                      jobs={match.keyword || []}
                      onSelect={openJob}
                    />
                    <RankedMatchList
                      title="Semantic match"
                      jobs={match.semantic || []}
                      onSelect={openJob}
                    />
                  </div>
                  {match.disclaimer ? (
                    <p className="text-xs text-ink/50">{match.disclaimer}</p>
                  ) : null}
                </>
              )}
            </>
          )}
          {selected ? (
            <Panel title="Job detail">
              <div className="space-y-3 text-sm">
                <h3 className="font-display text-xl text-ink">{String(selected.title)}</h3>
                <p className="text-ink/60">
                  {[selected.company, selected.location, selected.category]
                    .filter(Boolean)
                    .join(" · ")}
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
              </div>
            </Panel>
          ) : null}
        </div>
      ) : (
        <>
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
              <StatCard label="Matching jobs" value={loading ? "…" : (data?.total ?? "—")} />
              {loading && <p className="text-sm text-ink/50">Loading jobs…</p>}
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
              {!loading && (data?.jobs || []).length === 0 && !error ? (
                <p className="text-sm text-ink/50">No jobs match these filters.</p>
              ) : null}
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
        </>
      )}
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
