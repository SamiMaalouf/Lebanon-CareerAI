"use client";

import { Panel } from "./Charts";

export type RankedJob = {
  job_id: string;
  title: string;
  company?: string | null;
  location?: string | null;
  category?: string | null;
  compatibility_score?: number;
  matched_skills?: string[];
  missing_skills?: string[];
  matched_count?: number;
  listed_count?: number;
  is_internship?: boolean;
  seniority?: "fit" | "stretch";
  band?: "apply" | "learn";
  source_url?: string | null;
};

function JobCard({
  job,
  onSelect,
}: {
  job: RankedJob;
  onSelect?: (jobId: string) => void;
}) {
  const matched = job.matched_count;
  const listed = job.listed_count;
  const showCover = typeof matched === "number" && typeof listed === "number" && listed > 0;
  const inner = (
    <>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium text-ink">{job.title}</span>
        {job.compatibility_score != null ? (
          <span className="text-xs text-sea">{Math.round(job.compatibility_score)}% match</span>
        ) : null}
      </div>
      <p className="mt-0.5 text-xs text-ink/55">
        {[job.company, job.location, job.category].filter(Boolean).join(" · ")}
      </p>
      <div className="mt-1 flex flex-wrap gap-1.5">
        {job.is_internship ? (
          <span className="rounded-full bg-sea/15 px-2 py-0.5 text-xs text-sea">Internship</span>
        ) : null}
        {job.seniority === "stretch" ? (
          <span className="rounded-full bg-cedar/10 px-2 py-0.5 text-xs text-cedar">
            Senior / stretch
          </span>
        ) : null}
      </div>
      {showCover ? (
        <p className="mt-1 text-xs text-ink/70">
          Covers {matched} of {listed} tool{listed === 1 ? "" : "s"} listed in this ad
          {listed === 1 ? " — a short list scores high if you have that one tool" : ""}
        </p>
      ) : null}
      {(job.matched_skills || []).length > 0 && (
        <p className="mt-1 text-xs text-sea">You match: {job.matched_skills!.slice(0, 6).join(", ")}</p>
      )}
      {(job.missing_skills || []).length > 0 && (
        <p className="mt-1 text-xs text-ink/60">
          This ad also wants: {job.missing_skills!.slice(0, 4).join(", ")}
        </p>
      )}
    </>
  );

  if (onSelect) {
    return (
      <button
        type="button"
        onClick={() => onSelect(job.job_id)}
        className="w-full rounded-lg border border-cedar/15 bg-cream px-3 py-2 text-left text-sm hover:border-cedar/40"
      >
        {inner}
      </button>
    );
  }
  return (
    <div className="rounded-lg border border-cedar/15 bg-cream px-3 py-2 text-sm">
      {inner}
      {job.source_url ? (
        <a
          className="mt-2 inline-block text-xs text-sea underline"
          href={job.source_url}
          target="_blank"
          rel="noreferrer"
        >
          Open posting
        </a>
      ) : null}
    </div>
  );
}

function Group({ label, jobs, onSelect }: { label: string; jobs: RankedJob[]; onSelect?: (id: string) => void }) {
  if (!jobs.length) return null;
  return (
    <div className="space-y-2">
      <h3 className="text-xs font-medium uppercase tracking-wide text-ink/45">{label}</h3>
      <ul className="space-y-2">
        {jobs.map((job) => (
          <li key={job.job_id}>
            <JobCard job={job} onSelect={onSelect} />
          </li>
        ))}
      </ul>
    </div>
  );
}

export function RankedMatchList({
  title,
  jobs,
  onSelect,
}: {
  title: string;
  jobs: RankedJob[];
  onSelect?: (jobId: string) => void;
}) {
  const apply = jobs.filter((j) => j.band === "apply");
  const learn = jobs.filter((j) => j.band !== "apply");

  return (
    <Panel title={title}>
      {jobs.length ? (
        <div className="space-y-5">
          <Group label="Ready to apply" jobs={apply} onSelect={onSelect} />
          <Group label="Learn first" jobs={learn} onSelect={onSelect} />
        </div>
      ) : (
        <p className="text-sm text-ink/50">No ranked jobs for this profile yet.</p>
      )}
    </Panel>
  );
}
