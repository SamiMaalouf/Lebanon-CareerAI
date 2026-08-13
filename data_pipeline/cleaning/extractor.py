from __future__ import annotations

import re
from typing import Any

from data_pipeline.taxonomy.loader import SkillTaxonomy, load_taxonomy

PREFERRED_CUES = re.compile(
    r"(?i)\b(preferred|nice to have|advantage|plus|asset|desirable|bonus)\b"
)
REQUIRED_CUES = re.compile(
    r"(?i)\b(required|must have|mandatory|essential|minimum|you must)\b"
)

EDU_PATTERNS = [
    (re.compile(r"(?i)\bph\.?d\b|doctorate"), "PhD"),
    (re.compile(r"(?i)\bmaster'?s?\b|\bm\.?sc?\b|\bmba\b"), "Master's"),
    (re.compile(r"(?i)\bbachelor'?s?\b|\bb\.?sc?\b|\bb\.?e\.?\b|\bb\.?eng\b"), "Bachelor's"),
]

DEGREE_FIELDS = [
    (
        re.compile(
            r"(?i)computer\s*(?:and|&)?\s*communications?\s*engineering|"
            r"computer\s*engineering|comp\.?\s*eng\.?|\bcce\b"
        ),
        "Software Engineering",
    ),
    (re.compile(r"(?i)computer science|software engineering|informatics|génie\s*informatique"), "Software Engineering"),
    (re.compile(r"(?i)mechatronics"), "Mechatronics Engineering"),
    (re.compile(r"(?i)electrical engineering|electrical eng"), "Electrical Engineering"),
    (re.compile(r"(?i)mechanical engineering|mechanical eng"), "Mechanical Engineering"),
    (re.compile(r"(?i)civil engineering"), "Civil Engineering"),
    (re.compile(r"(?i)architecture"), "Architecture"),
    (re.compile(r"(?i)electronics"), "Electronics Engineering"),
    (re.compile(r"(?i)automation|industrial engineering"), "Automation Engineering"),
    (re.compile(r"(?i)robotics"), "Robotics"),
    (re.compile(r"(?i)artificial intelligence|machine learning"), "Artificial Intelligence"),
    (re.compile(r"(?i)web\s*development|web\s*engineering"), "Web Development"),
    (re.compile(r"(?i)data\s*science|data\s*engineering"), "Data Science"),
    (re.compile(r"(?i)cyber\s*security|cybersecurity|information\s*security"), "Cybersecurity"),
]

EXP_PATTERNS = [
    (re.compile(r"(?i)\bintern(ship)?\b"), "Internship"),
    (re.compile(r"(?i)\b(entry[- ]level|junior|graduate|fresh graduate)\b"), "Entry-level"),
    (re.compile(r"(?i)\b(0\s*[-–to]+\s*2|1\s*[-–to]+\s*2)\s*years?\b"), "0-2 years"),
    (re.compile(r"(?i)\b(2\s*[-–to]+\s*5|3\s*[-–to]+\s*5)\s*years?\b"), "2-5 years"),
    (re.compile(r"(?i)\b(5\s*\+|5\s*[-–to]+\s*\d+|senior|lead)\s*(years?)?\b"), "5+ years"),
]

LANG_PATTERNS = [
    (re.compile(r"(?i)\barabic\b|عربي"), "Arabic"),
    (re.compile(r"(?i)\benglish\b"), "English"),
    (re.compile(r"(?i)\bfrench\b|fran[cç]ais"), "French"),
]


class JobExtractor:
    def __init__(self, taxonomy: SkillTaxonomy | None = None):
        self.taxonomy = taxonomy or load_taxonomy()
        self._alias_patterns = self.taxonomy.all_alias_patterns()
        locations = []
        try:
            import yaml
            from pathlib import Path

            raw = yaml.safe_load(Path(self.taxonomy.path).read_text(encoding="utf-8"))
            locations = raw.get("lebanese_locations") or []
        except Exception:
            locations = ["Beirut", "Tripoli", "Lebanon"]
        self.locations = locations

    def extract_skills(self, text: str) -> list[dict[str, Any]]:
        if not text:
            return []
        lower = text.lower()
        # Collect match spans; keep longest non-overlapping (prevents
        # "communication" firing inside "industrial communication").
        spans: list[tuple[int, int, str, bool]] = []
        for alias, skill_id in self._alias_patterns:
            pattern = re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)", re.IGNORECASE)
            for m in pattern.finditer(lower):
                start = max(0, m.start() - 80)
                window = lower[start : m.end() + 40]
                is_required = True
                if PREFERRED_CUES.search(window) and not REQUIRED_CUES.search(window):
                    is_required = False
                spans.append((m.start(), m.end(), skill_id, is_required))

        spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))
        chosen: list[tuple[int, int, str, bool]] = []
        occupied: list[tuple[int, int]] = []
        for start, end, skill_id, is_required in spans:
            if any(not (end <= a or start >= b) for a, b in occupied):
                continue
            occupied.append((start, end))
            chosen.append((start, end, skill_id, is_required))

        # Leaf skills only (skip category parents like "Languages", "Programming")
        parents_with_children = {
            meta.get("parent_id")
            for meta in self.taxonomy.skills.values()
            if meta.get("parent_id")
        }

        found: dict[str, dict[str, Any]] = {}
        for start, end, skill_id, is_required in chosen:
            if skill_id in parents_with_children:
                continue
            # Guard soft-skill false positives in technical phrases
            if skill_id == "communication":
                prefix = lower[max(0, start - 20) : start]
                if re.search(r"(industrial|data|network|protocol|radio)\s*$", prefix):
                    continue
            meta = self.taxonomy.skills[skill_id]
            if skill_id in found:
                found[skill_id]["is_required"] = found[skill_id]["is_required"] and is_required
            else:
                found[skill_id] = {
                    "skill_id": skill_id,
                    "name": meta["name"],
                    "is_required": is_required,
                    "confidence": 1.0,
                }
        return list(found.values())

    def extract_education(self, text: str) -> dict[str, Any]:
        level = None
        for pat, label in EDU_PATTERNS:
            if pat.search(text or ""):
                level = label
                break
        fields = [label for pat, label in DEGREE_FIELDS if pat.search(text or "")]
        return {"education_level": level, "education_fields": fields}

    def extract_experience_level(self, text: str) -> str | None:
        for pat, label in EXP_PATTERNS:
            if pat.search(text or ""):
                return label
        return None

    def extract_languages(self, text: str) -> list[str]:
        return [label for pat, label in LANG_PATTERNS if pat.search(text or "")]

    def extract_location(self, text: str, existing: str | None = None) -> str | None:
        if existing:
            for loc in self.locations:
                if loc.lower() in existing.lower():
                    return loc
        blob = text or ""
        for loc in sorted(self.locations, key=len, reverse=True):
            if re.search(rf"(?i)\b{re.escape(loc)}\b", blob):
                return loc
        return existing

    def extract_job(self, record: dict[str, Any]) -> dict[str, Any]:
        from data_pipeline.cleaning.engineering_filter import (
            ENGINEERING_CATEGORIES,
            classify_engineering_category,
            is_internship,
        )

        text = " ".join(
            filter(
                None,
                [
                    record.get("job_title"),
                    record.get("cleaned_text"),
                    record.get("description"),
                    record.get("requirements"),
                    record.get("preferred_skills"),
                    record.get("education"),
                    record.get("experience"),
                ],
            )
        )
        skills = self.extract_skills(text)
        edu = self.extract_education(text)
        title = record.get("job_title") or ""
        rule_cat, rule_conf = classify_engineering_category(title, text)
        existing = record.get("job_category")
        # Always prefer a fresh rule label so stale Software Engineering tags get fixed
        if rule_cat != "Other":
            job_category = rule_cat
            category_confidence = rule_conf
        elif existing in ENGINEERING_CATEGORIES:
            job_category = existing
            category_confidence = float(record.get("category_confidence") or 1.0)
        else:
            job_category = record.get("job_category") or "Other"
            category_confidence = float(record.get("category_confidence") or 0.0)

        internship = bool(record.get("is_internship")) or is_internship(title, text)
        exp = self.extract_experience_level(text) or record.get("experience_level")
        if internship and (not exp or exp == "Other"):
            exp = "Internship"

        return {
            **record,
            "extracted_skills": skills,
            "required_skills": [s["name"] for s in skills if s["is_required"]],
            "preferred_skills_list": [s["name"] for s in skills if not s["is_required"]],
            "education_level": edu["education_level"] or record.get("education_level"),
            "education_fields": edu["education_fields"],
            "experience_level": exp,
            "languages_extracted": self.extract_languages(text) or record.get("languages") or [],
            "location_normalized": self.extract_location(text, record.get("location")),
            "job_category": job_category,
            "category_confidence": category_confidence,
            "is_internship": internship,
        }
