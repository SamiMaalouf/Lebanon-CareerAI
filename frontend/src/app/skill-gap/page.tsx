"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Panel } from "../../components/Charts";
import { apiPost, loadProfile, type CandidateProfile } from "../../lib/api";
import { ENGINEERING_CATEGORIES, defaultEngineeringCategory } from "../../lib/categories";

type GapSkill = {
  skill: string;
  demand_pct: number;
  count?: number;
  jobs_in_scope?: number;
  required_rate_pct?: number;
  priority?: string;
  why?: string;
  cv_example?: string;
};

type GapResponse = {
  category: string;
  market_category?: string;
  job_count?: number;
  sparse?: boolean;
  possessed: GapSkill[];
  missing: GapSkill[];
  roadmap?: { skill: string; priority?: string; why?: string }[];
  disclaimer: string;
};

function requiredLabel(rate?: number): string {
  if (rate == null) return "";
  if (rate >= 50) return "often required";
  if (rate >= 25) return "sometimes required";
  return "usually preferred";
}

function countLabel(s: GapSkill): string {
  if (typeof s.count === "number" && typeof s.jobs_in_scope === "number") {
    return `${s.count}/${s.jobs_in_scope} ads`;
  }
  return `${s.demand_pct}% demand`;
}

function sparseNote(data: GapResponse): string | null {
  if (!data.sparse) return null;
  if (data.market_category && data.market_category !== data.category) {
    return `No ${data.category} ads in this dataset yet — using ${data.job_count} ${data.market_category} postings as the closest bucket.`;
  }
  return `Only ${data.job_count} posting${data.job_count === 1 ? "" : "s"} in ${data.category} — treat percentages as a lighter signal.`;
}

function gapPayload(profile: CandidateProfile, category: string) {
  return {
    skills: profile.skills,
    education_level: profile.education_level,
    education_fields: profile.education_fields,
    experience_level: profile.experience_level,
    target_categories: profile.target_categories,
    category,
    top_n: 15,
  };
}

function PathColumn({ data }: { data: GapResponse }) {
  const note = sparseNote(data);
  const possessed = data.possessed || [];
  const missing = data.missing || [];
  const jobsHref = (skill: string) =>
    `/jobs?skill=${encodeURIComponent(skill)}&category=${encodeURIComponent(data.category)}`;
  return (
    <div className="space-y-3">
      <div>
        <h2 className="font-display text-2xl text-cedar">{data.category}</h2>
        <p className="text-xs text-ink/50">
          {data.job_count ?? 0} ads
          {data.market_category && data.market_category !== data.category
            ? ` (via ${data.market_category})`
            : ""}
        </p>
      </div>
      {note ? <p className="text-xs text-ink/55">{note}</p> : null}
      <p className="text-xs text-ink/55">
        {possessed.length
          ? `${possessed.length} of your tools appear in this market: ${possessed.map((s) => s.skill).join(", ")}`
          : "None of your listed tools appear in this category's ads yet."}
      </p>
      <Panel title="Missing vs this path">
        {missing.length ? (
          <ul className="space-y-2">
            {missing.map((s) => (
              <li key={s.skill} className="rounded-lg border border-cedar/10 bg-cream px-3 py-2 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <Link
                    href={jobsHref(s.skill)}
                    className="font-medium text-ink underline decoration-cedar/30 hover:text-cedar"
                  >
                    {s.skill}
                  </Link>
                  {s.priority ? (
                    <span className="rounded-full bg-cedar/10 px-2 py-0.5 text-xs text-cedar">
                      {s.priority}
                    </span>
                  ) : null}
                </div>
                <p className="mt-0.5 text-xs text-ink/55">
                  {countLabel(s)}
                  {s.required_rate_pct != null ? ` · ${requiredLabel(s.required_rate_pct)}` : ""}
                </p>
                {s.cv_example ? (
                  <p className="mt-1 text-xs text-sea">{s.cv_example}</p>
                ) : null}
                {s.why ? <p className="mt-1 text-xs text-ink/60">{s.why}</p> : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-ink/50">No extra technical skills flagged for this category.</p>
        )}
      </Panel>
    </div>
  );
}

export default function SkillGapPage() {
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [categoryA, setCategoryA] = useState("Software Engineering");
  const [categoryB, setCategoryB] = useState("Web Development");
  const [dataA, setDataA] = useState<GapResponse | null>(null);
  const [dataB, setDataB] = useState<GapResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const saved = loadProfile();
    if (!saved?.skills?.length) return;
    setProfile(saved);
    const a = defaultEngineeringCategory(saved.target_categories, "Software Engineering");
    setCategoryA(a);
    const others = (saved.target_categories || [])
      .map((c) => defaultEngineeringCategory([c], a))
      .filter((c) => c !== a);
    const fallbackB = a === "Web Development" ? "Software Engineering" : "Web Development";
    const b = others[0] || fallbackB;
    setCategoryB(b === a ? (ENGINEERING_CATEGORIES.find((c) => c !== a) || fallbackB) : b);
  }, []);

  useEffect(() => {
    if (!profile?.skills?.length) return;
    let cancelled = false;
    setBusy(true);
    setError(null);
    Promise.all([
      apiPost<GapResponse>("/api/skill-gap", gapPayload(profile, categoryA)),
      apiPost<GapResponse>("/api/skill-gap", gapPayload(profile, categoryB)),
    ])
      .then(([left, right]) => {
        if (!cancelled) {
          setDataA(left);
          setDataB(right);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed");
          setDataA(null);
          setDataB(null);
        }
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [profile, categoryA, categoryB]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-4xl text-cedar">Skill Gap</h1>
        <p className="mt-2 text-ink/65">
          Same CV, two career paths — see which technical skills Lebanese ads ask for, and how to
          show each one on your CV.
        </p>
      </div>

      {!profile?.skills?.length ? (
        <Panel title="No CV loaded">
          <p className="text-sm text-ink/70">
            Upload or paste a CV first so this table is about you, not a demo profile.
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
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-sm">
              <span className="text-ink/60">Path A</span>
              <select
                className="mt-1 block min-w-[16rem] rounded-lg border border-cedar/20 bg-cream px-3 py-2"
                value={categoryA}
                onChange={(e) => setCategoryA(e.target.value)}
              >
                {ENGINEERING_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              <span className="text-ink/60">Path B</span>
              <select
                className="mt-1 block min-w-[16rem] rounded-lg border border-cedar/20 bg-cream px-3 py-2"
                value={categoryB}
                onChange={(e) => setCategoryB(e.target.value)}
              >
                {ENGINEERING_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink/45">
              Skills used from your CV
            </p>
            <div className="flex flex-wrap gap-1.5">
              {profile.skills.map((s) => (
                <span key={s} className="rounded-md bg-sand px-2 py-0.5 text-xs text-ink/80">
                  {s}
                </span>
              ))}
            </div>
          </div>

          {error && <p className="text-sm text-cedar">{error}</p>}
          {busy && (
            <p className="text-sm text-ink/50">
              Comparing {categoryA} and {categoryB}…
            </p>
          )}

          {dataA && dataB && !busy && (
            <>
              <div className="grid gap-6 lg:grid-cols-2">
                <PathColumn data={dataA} />
                <PathColumn data={dataB} />
              </div>
              {(dataA.roadmap || []).length > 0 ? (
                <Panel
                  title={`Learn next · ${dataA.category}`}
                  subtitle="Highest-priority missing skills from this dataset — not a guaranteed curriculum"
                >
                  <ol className="list-decimal space-y-2 pl-5 text-sm">
                    {dataA.roadmap!.slice(0, 6).map((step) => (
                      <li key={step.skill}>
                        <Link
                          href={`/jobs?skill=${encodeURIComponent(step.skill)}&category=${encodeURIComponent(dataA.category)}`}
                          className="font-medium text-ink underline decoration-cedar/30 hover:text-cedar"
                        >
                          {step.skill}
                        </Link>
                        {step.priority ? (
                          <span className="ml-2 text-xs text-cedar">{step.priority}</span>
                        ) : null}
                        {step.why ? <p className="mt-0.5 text-xs text-ink/60">{step.why}</p> : null}
                      </li>
                    ))}
                  </ol>
                  <Link
                    href={`/jobs?forYou=1&category=${encodeURIComponent(dataA.category)}`}
                    className="mt-4 inline-block text-sm text-sea underline"
                  >
                    See ranked {dataA.category} jobs for your CV
                  </Link>
                </Panel>
              ) : null}
              <p className="text-xs text-ink/55">{dataA.disclaimer}</p>
            </>
          )}
        </>
      )}
    </div>
  );
}
