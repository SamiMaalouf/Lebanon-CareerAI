"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Panel } from "../../components/Charts";
import {
  apiPost,
  apiUpload,
  loadProfile,
  saveProfile,
  type CandidateProfile,
} from "../../lib/api";
import {
  ENGINEERING_CATEGORIES,
  defaultEngineeringCategory,
} from "../../lib/categories";

type AnalyzedProfile = CandidateProfile & {
  projects_section_found?: boolean;
  detected_sections?: string[];
  project_hint_lines?: string[];
  privacy_note?: string;
};

type CoachFix = {
  id: string;
  ok: boolean;
  title: string;
  action: string;
};

type CoachSkill = {
  skill: string;
  demand_pct?: number;
  action?: string;
};

type CoachJob = {
  job_id: string;
  title: string;
  company?: string | null;
  location?: string | null;
  source_url?: string | null;
  is_internship?: boolean;
  compatibility_score?: number;
  matched_skills?: string[];
  missing_skills?: string[];
};

type CoachResponse = {
  category: string;
  market_category?: string;
  job_count: number;
  sparse: boolean;
  cv_fixes: CoachFix[];
  learn_next: CoachSkill[];
  strengths: CoachSkill[];
  apply_now: CoachJob[];
  disclaimer: string;
};

export default function CVPage() {
  const [profile, setProfile] = useState<AnalyzedProfile | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [coachCategory, setCoachCategory] = useState<string>("Software Engineering");
  const [coach, setCoach] = useState<CoachResponse | null>(null);
  const [coachBusy, setCoachBusy] = useState(false);
  const [coachError, setCoachError] = useState<string | null>(null);

  useEffect(() => {
    const saved = loadProfile();
    if (saved) setProfile(saved);
  }, []);

  useEffect(() => {
    if (!profile) {
      setCoach(null);
      return;
    }
    setCoachCategory(
      defaultEngineeringCategory(profile.target_categories, "Software Engineering")
    );
  }, [profile]);

  useEffect(() => {
    if (!profile) return;
    let cancelled = false;
    setCoachBusy(true);
    setCoachError(null);
    apiPost<CoachResponse>("/api/cv/coach", {
      skills: profile.skills,
      education_level: profile.education_level,
      education_fields: profile.education_fields,
      experience_level: profile.experience_level,
      languages: profile.languages,
      projects: profile.projects,
      target_categories: profile.target_categories,
      detected_sections: profile.detected_sections,
      projects_section_found: profile.projects_section_found,
      category: coachCategory,
    })
      .then((res) => {
        if (!cancelled) setCoach(res);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setCoachError(e instanceof Error ? e.message : "Coach failed");
          setCoach(null);
        }
      })
      .finally(() => {
        if (!cancelled) setCoachBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [profile, coachCategory]);

  async function onUpload(file: File) {
    setBusy(true);
    setError(null);
    try {
      const result = await apiUpload<AnalyzedProfile>("/api/cv/analyze", file);
      setProfile(result);
      saveProfile(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function onAnalyzeText() {
    setBusy(true);
    setError(null);
    try {
      const result = await apiPost<AnalyzedProfile>("/api/cv/analyze-text", { text });
      setProfile(result);
      saveProfile(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  }

  const jobsHref = `/jobs?category=${encodeURIComponent(coachCategory)}`;
  const internshipsHref = `/internships?forYou=1&category=${encodeURIComponent(coachCategory)}`;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-4xl text-cedar">CV Analyzer</h1>
        <p className="mt-2 text-ink/65">
          Upload a PDF or DOCX CV for Lebanese engineering career feedback. Files are processed
          ephemerally and not stored permanently.
        </p>
      </div>

      <Panel title="Upload CV">
        <input
          type="file"
          accept=".pdf,.docx,.txt"
          disabled={busy}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onUpload(f);
          }}
        />
        <p className="mt-3 text-xs text-ink/50">Supported: PDF, DOCX, TXT (max 8MB)</p>
      </Panel>

      <Panel title="Or paste CV text">
        <textarea
          className="min-h-40 w-full rounded-lg border border-cedar/20 bg-cream p-3 text-sm"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste education, skills, projects…"
        />
        <button
          type="button"
          disabled={busy || !text.trim()}
          onClick={onAnalyzeText}
          className="mt-3 rounded-lg bg-cedar px-4 py-2 text-sm text-cream disabled:opacity-50"
        >
          {busy ? "Analyzing…" : "Analyze text"}
        </button>
      </Panel>

      {error && <p className="text-sm text-cedar">{error}</p>}

      {profile && (
        <>
          <div className="grid gap-6 lg:grid-cols-2">
            <Panel title="Extracted skills">
              <div className="flex flex-wrap gap-2">
                {(profile.skills || []).length ? (
                  profile.skills.map((s) => (
                    <span key={s} className="rounded-md bg-sand px-2 py-1 text-sm">
                      {s}
                    </span>
                  ))
                ) : (
                  <p className="text-sm text-ink/50">No taxonomy skills detected yet.</p>
                )}
              </div>
            </Panel>
            <Panel title="Education & experience">
              <ul className="space-y-1 text-sm text-ink/80">
                <li>Level: {profile.education_level || "—"}</li>
                <li>Fields: {(profile.education_fields || []).join(", ") || "—"}</li>
                <li>Experience: {profile.experience_level || "—"}</li>
                <li>Languages: {(profile.languages || []).join(", ") || "—"}</li>
              </ul>
            </Panel>
            <Panel
              title="Project titles"
              subtitle="Main ideas from your Projects section only — not other CV sections"
            >
              <ul className="list-disc space-y-1 pl-5 text-sm">
                {(profile.projects || []).length ? (
                  profile.projects!.map((p) => <li key={p}>{p}</li>)
                ) : (
                  <li className="list-none text-ink/50">
                    {profile.projects_section_found === false ||
                    profile.projects_section_found === undefined
                      ? "No Projects section detected. Add a clear “Projects” or “Academic Projects” heading."
                      : "Projects section found, but no clear project titles were extracted."}
                  </li>
                )}
              </ul>
              {(profile.detected_sections || []).length > 0 && (
                <p className="mt-3 text-xs text-ink/50">
                  Detected sections:{" "}
                  {profile.detected_sections!.map((s) => s.charAt(0).toUpperCase() + s.slice(1)).join(", ")}
                </p>
              )}
              {(profile.project_hint_lines || []).length > 0 &&
                !profile.projects_section_found && (
                  <div className="mt-3 rounded-lg border border-cedar/15 bg-sand/40 p-3 text-xs text-ink/65">
                    <p className="mb-1 font-medium text-ink/80">
                      Lines mentioning “project” in the extracted text (not treated as a section
                      heading):
                    </p>
                    <ul className="list-disc space-y-1 pl-4">
                      {profile.project_hint_lines!.map((ln) => (
                        <li key={ln} className="break-words">
                          {ln}
                        </li>
                      ))}
                    </ul>
                    <p className="mt-2">
                      If your heading is an image/icon-only title, or the CV is a multi-column
                      design, try a plain-text “Projects” heading on its own line, or paste that
                      section into Analyze text.
                    </p>
                  </div>
                )}
            </Panel>
            <Panel title="Inferred education fields">
              <div className="flex flex-wrap gap-2">
                {(profile.target_categories || []).length ? (
                  profile.target_categories!.map((s) => (
                    <span key={s} className="rounded-md bg-sea/10 px-2 py-1 text-sm text-sea">
                      {s}
                    </span>
                  ))
                ) : (
                  <p className="text-sm text-ink/50">None inferred from education text.</p>
                )}
              </div>
            </Panel>
          </div>

          <Panel
            title="CV Coach"
            subtitle="What to fix on this CV, which tools to show next, and where to apply"
          >
            <div className="mb-4 flex flex-wrap items-end gap-3">
              <label className="text-sm">
                <span className="text-ink/60">Target engineering path</span>
                <select
                  className="mt-1 block min-w-[16rem] rounded-lg border border-cedar/20 bg-cream px-3 py-2"
                  value={coachCategory}
                  onChange={(e) => setCoachCategory(e.target.value)}
                >
                  {ENGINEERING_CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {coachBusy && <p className="text-sm text-ink/50">Reviewing your CV against {coachCategory}…</p>}
            {coachError && <p className="text-sm text-cedar">{coachError}</p>}

            {coach && !coachBusy && (
              <div className="space-y-6">
                {coach.sparse && (
                  <p className="text-sm text-ink/55">
                    {coach.market_category && coach.market_category !== coach.category
                      ? `No ${coach.category} ads in this dataset yet — using ${coach.job_count} ${coach.market_category} postings as the closest bucket.`
                      : `Only ${coach.job_count} posting${coach.job_count === 1 ? "" : "s"} in ${coachCategory} in this dataset — treat tips as a lighter signal.`}
                  </p>
                )}

                <div>
                  <h3 className="mb-2 text-sm font-medium text-ink">1. Fix your CV</h3>
                  {((coach.cv_fixes || []).filter((f) => f.ok === false)).length ? (
                    <ul className="space-y-2">
                      {coach.cv_fixes
                        .filter((f) => f.ok === false)
                        .map((fix) => (
                        <li
                          key={fix.id}
                          className="flex gap-3 rounded-lg border border-cedar/10 bg-sand/30 px-3 py-2 text-sm"
                        >
                          <span className="mt-0.5 shrink-0 text-xs font-medium text-cedar">
                            Fix
                          </span>
                          <div>
                            <div className="font-medium text-ink">{fix.title}</div>
                            <p className="text-ink/65">{fix.action}</p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-ink/55">No structural issues detected on this CV.</p>
                  )}
                </div>

                <div>
                  <h3 className="mb-2 text-sm font-medium text-ink">2. Show these skills next</h3>
                  {(coach.strengths || []).length > 0 && (
                    <p className="mb-2 text-sm text-ink/70">
                      Already useful on this CV:{" "}
                      {coach.strengths.map((s) => s.skill).join(", ")}
                    </p>
                  )}
                  {(coach.learn_next || []).length ? (
                    <ul className="space-y-2">
                      {coach.learn_next.map((item) => (
                        <li
                          key={item.skill}
                          className="rounded-lg border border-cedar/10 bg-cream px-3 py-2 text-sm"
                        >
                          <Link
                            href={`/jobs?skill=${encodeURIComponent(item.skill)}&category=${encodeURIComponent(coachCategory)}`}
                            className="font-medium text-ink underline decoration-cedar/30 hover:text-cedar"
                          >
                            {item.skill}
                          </Link>
                          {item.action ? (
                            <p className="mt-1 text-ink/65">{item.action}</p>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-ink/50">
                      No extra technical skills flagged for this category.
                    </p>
                  )}
                </div>

                <div>
                  <h3 className="mb-2 text-sm font-medium text-ink">3. Apply to these</h3>
                  {(coach.apply_now || []).length ? (
                    <ul className="space-y-2">
                      {coach.apply_now.map((job) => (
                        <li
                          key={job.job_id}
                          className="rounded-lg border border-cedar/15 bg-sand/20 px-3 py-3 text-sm"
                        >
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-medium text-ink">{job.title}</span>
                            {job.compatibility_score != null ? (
                              <span className="rounded-full bg-sea/15 px-2 py-0.5 text-xs text-sea">
                                {Math.round(job.compatibility_score)}% match
                              </span>
                            ) : null}
                            {job.is_internship ? (
                              <span className="rounded-full bg-sea/15 px-2 py-0.5 text-xs text-sea">
                                Internship
                              </span>
                            ) : null}
                          </div>
                          <p className="mt-0.5 text-ink/55">
                            {[job.company, job.location].filter(Boolean).join(" · ")}
                          </p>
                          {(job.matched_skills || []).length > 0 && (
                            <p className="mt-1 text-xs text-sea">
                              You match: {job.matched_skills!.join(", ")}
                            </p>
                          )}
                          {(job.missing_skills || []).length > 0 && (
                            <p className="mt-1 text-xs text-ink/60">
                              This ad also wants: {job.missing_skills!.join(", ")}
                            </p>
                          )}
                          {job.source_url ? (
                            <a
                              className="mt-2 inline-block text-sea underline"
                              href={job.source_url}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Open posting
                            </a>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-ink/50">
                      No postings in this category yet. Try another path or browse all jobs.
                    </p>
                  )}
                </div>

                <div className="flex flex-wrap gap-3">
                  <Link
                    href={internshipsHref}
                    className="rounded-lg bg-sea px-4 py-2 text-sm text-cream hover:opacity-90"
                  >
                    All internships
                  </Link>
                  <Link
                    href={jobsHref}
                    className="rounded-lg border border-cedar/30 bg-cream px-4 py-2 text-sm text-cedar hover:bg-sand"
                  >
                    All {coachCategory} jobs
                  </Link>
                  <Link
                    href="/skill-gap"
                    className="rounded-lg border border-cedar/20 px-4 py-2 text-sm text-ink/70 hover:bg-sand"
                  >
                    Skill-gap table
                  </Link>
                  <Link
                    href={`/jobs?forYou=1&category=${encodeURIComponent(coachCategory)}`}
                    className="rounded-lg border border-cedar/20 px-4 py-2 text-sm text-ink/70 hover:bg-sand"
                  >
                    Ranked jobs for you
                  </Link>
                </div>
                {coach.disclaimer ? (
                  <p className="text-xs text-ink/50">{coach.disclaimer}</p>
                ) : null}
              </div>
            )}
          </Panel>
        </>
      )}
    </div>
  );
}
