"""Run all Lebanese public-board collectors and merge into one JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.collectors import daleel_el3amal, daleel_madani, hirelebanese, jobs_for_lebanon, jobslebanon
from data_pipeline.collectors.quality import filter_jobs
from data_pipeline.cleaning.engineering_filter import filter_engineering_jobs
from data_pipeline.cleaning.pipeline import content_hash


def merge_jobs(batches: list[list[dict]]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for batch in batches:
        for job in batch:
            key = job.get("job_id") or content_hash(
                job.get("job_title") or "",
                job.get("company"),
                job.get("description"),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(job)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect real Lebanese engineering job postings")
    parser.add_argument("--min-jobs", type=int, default=200, help="Min clean jobs before eng filter")
    parser.add_argument("--min-eng-jobs", type=int, default=100)
    parser.add_argument("--hire-max", type=int, default=1000)
    parser.add_argument("--hire-pages", type=int, default=40)
    parser.add_argument("--jfl-max", type=int, default=700)
    parser.add_argument("--skip-hire", action="store_true")
    parser.add_argument("--skip-jfl", action="store_true")
    parser.add_argument("--min-description", type=int, default=80)
    args = parser.parse_args()

    batches: list[list[dict]] = []

    print("=== JobsLebanon ===")
    batches.append(jobslebanon.collect(max_jobs=300))

    print("=== Daleel el 3amal ===")
    batches.append(daleel_el3amal.collect(max_jobs=250))

    print("=== Daleel Madani ===")
    batches.append(daleel_madani.collect(max_jobs=150))

    if not args.skip_jfl:
        print("=== Jobs for Lebanon (eng-biased listing) ===")
        batches.append(jobs_for_lebanon.collect(max_jobs=args.jfl_max, max_list_pages=40))

    if not args.skip_hire:
        print("=== HireLebanese eng keyword lists (best-effort) ===")
        batches.append(
            hirelebanese.collect(max_jobs=args.hire_max, max_list_pages=args.hire_pages)
        )

    merged = merge_jobs(batches)
    cleaned, reasons = filter_jobs(merged, min_description=args.min_description)
    print(f"Quality filter: {len(merged)} -> {len(cleaned)} | {reasons}")

    out = ROOT / "raw_data" / "real_jobs_merged.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Merged {len(cleaned)} clean real jobs -> {out}")

    eng, eng_reasons = filter_engineering_jobs(cleaned)
    eng_out = ROOT / "raw_data" / "engineering_jobs_merged.json"
    eng_out.write_text(json.dumps(eng, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Engineering filter: {len(cleaned)} -> {len(eng)} | {eng_reasons}")
    print(f"Engineering subset -> {eng_out}")

    if len(cleaned) < args.min_jobs:
        print(
            f"WARNING: only {len(cleaned)} jobs (< {args.min_jobs}). "
            "Re-run with higher --hire-pages/--hire-max or add imports."
        )
        sys.exit(2)
    if len(eng) < args.min_eng_jobs:
        print(
            f"WARNING: only {len(eng)} engineering jobs (< {args.min_eng_jobs}). "
            "Collectors may need another pass with eng keyword bias."
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
