"""
Quick smoke checks used during development.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    from data_pipeline.taxonomy.loader import load_taxonomy
    from data_pipeline.cleaning.extractor import JobExtractor
    from data_pipeline.cleaning.pipeline import clean_job

    tax = load_taxonomy()
    assert "plc" in tax.skills or "siemens_plc" in tax.alias_to_id.values()
    ex = JobExtractor(tax)
    skills = ex.extract_skills(
        "Siemens PLC and TIA Portal; industrial communication protocols; SolidWorks preferred"
    )
    names = {s["name"] for s in skills}
    assert "TIA Portal" in names
    assert "SolidWorks" in names
    cleaned = clean_job({"job_title": "Test", "description": "<b>Hello</b>  world"})
    assert "<" not in cleaned["cleaned_text"]
    print("smoke ok", sorted(names))


if __name__ == "__main__":
    main()
