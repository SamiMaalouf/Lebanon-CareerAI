"""Engineering-focused top-up collection: merge new eng listings into existing corpus."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.cleaning.engineering_filter import filter_engineering_jobs
from data_pipeline.cleaning.pipeline import content_hash
from data_pipeline.collectors import hirelebanese, jobs_for_lebanon, jobslebanon
from data_pipeline.collectors.quality import filter_jobs


def merge(batches: list[list[dict]]) -> list[dict]:
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
    existing_path = ROOT / "raw_data" / "real_jobs_merged.json"
    existing = []
    if existing_path.exists():
        existing = json.loads(existing_path.read_text(encoding="utf-8"))
        print(f"Loaded existing {len(existing)} jobs")

    print("=== JobsLebanon top-up ===")
    jl = jobslebanon.collect(max_jobs=300)

    print("=== Jobs for Lebanon eng-biased top-up ===")
    jfl = jobs_for_lebanon.collect(max_jobs=800, max_list_pages=20)

    print("=== HireLebanese eng keyword top-up ===")
    # Prefer keyword depth over full generic crawl volume
    hl = hirelebanese.collect(max_jobs=1200, max_list_pages=25)

    merged = merge([existing, jl, jfl, hl])
    cleaned, q_reasons = filter_jobs(merged, min_description=80)
    print(f"Quality: {len(merged)} -> {len(cleaned)} | {q_reasons}")

    existing_path.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {existing_path} ({len(cleaned)})")

    eng, eng_reasons = filter_engineering_jobs(cleaned)
    eng_path = ROOT / "raw_data" / "engineering_jobs_merged.json"
    eng_path.write_text(json.dumps(eng, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Engineering: {len(cleaned)} -> {len(eng)} | {eng_reasons}")
    print(f"Wrote {eng_path}")


if __name__ == "__main__":
    main()
