"""CV text extraction and structured profile analysis."""

from __future__ import annotations

import io
import re
import tempfile
from pathlib import Path
from typing import Any

from data_pipeline.cleaning.extractor import JobExtractor
from data_pipeline.taxonomy.loader import load_taxonomy

# Longest-first aliases → canonical section name
HEADER_ALIASES: list[tuple[str, str]] = [
    ("academic background", "education"),
    ("professional experience", "experience"),
    ("work experience", "experience"),
    ("project experience", "projects"),
    ("academic projects", "projects"),
    ("personal projects", "projects"),
    ("selected projects", "projects"),
    ("undergraduate projects", "projects"),
    ("university projects", "projects"),
    ("graduation project", "projects"),
    ("final year project", "projects"),
    ("final year projects", "projects"),
    ("senior project", "projects"),
    ("senior design project", "projects"),
    ("capstone project", "projects"),
    ("relevant projects", "projects"),
    ("featured projects", "projects"),
    ("side projects", "projects"),
    ("key projects", "projects"),
    ("major projects", "projects"),
    ("my projects", "projects"),
    ("projects and research", "projects"),
    ("projects & research", "projects"),
    ("technical skills", "skills"),
    ("core competencies", "skills"),
    ("language skills", "languages"),
    ("about me", "summary"),
    ("education", "education"),
    ("expérience", "experience"),
    ("experience", "experience"),
    ("employment", "experience"),
    ("portfolio", "projects"),
    ("projects", "projects"),
    ("project", "projects"),
    ("skills", "skills"),
    ("technologies", "skills"),
    ("certifications", "certifications"),
    ("certificates", "certifications"),
    ("languages", "languages"),
    ("langues", "languages"),
    ("summary", "summary"),
    ("profile", "summary"),
    ("objective", "summary"),
]

# Action / bullet openers — always description, never project titles
ACTION_START = re.compile(
    r"(?i)^(built|developed|implemented|designed|created|secured|configured|"
    r"integrated|optimized|utilized|leveraged|applied|performed|conducted|"
    r"achieved|improved|enhanced|maintained|collaborated|worked|led|managed|"
    r"wrote|trained|deployed|tested|analyzed|used|using|with|responsible|"
    r"technologies|tech\s*stack|tools|stack|role|description|summary|"
    r"focused|helped|enabled|provided|supported|engineered|architected)\b"
)
TECH_ONLY = re.compile(
    r"(?i)^(python|java|c\+\+|javascript|typescript|react|node\.?js|matlab|solidworks|"
    r"arduino|sql|html|css|aws|docker|git|fastapi|django|flask|langchain|"
    r"pytorch|tensorflow|kubernetes|mongodb|postgresql|mysql|redis)"
    r"([,\s/|&]+(python|java|c\+\+|javascript|typescript|react|node\.?js|matlab|"
    r"solidworks|arduino|sql|html|css|aws|docker|git|fastapi|django|flask|"
    r"langchain|pytorch|tensorflow|kubernetes|mongodb|postgresql|mysql|redis))*$"
)

TITLE_SPLIT = re.compile(r"\s+[—–|:]\s+|\s+-\s+")
LEADING_DECOR = re.compile(
    r"^[\s\|\-\u2013\u2014\u2022\u25cf\u25a0\u25b6\u25c6\u25aa\u25ab\*●▪◦■◆▶►❖·]+|"
    r"^\d{1,2}[\.\)\-]\s*"
)


def _normalize_line(raw: str) -> str:
    s = (raw or "").replace("\u00ad", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _prep_header_line(raw: str) -> str:
    """Normalize and strip bullets/icons/numbers before header matching."""
    return LEADING_DECOR.sub("", _normalize_line(raw)).strip()


def _match_alias_at(low: str, start: int = 0) -> tuple[str, str, int] | None:
    """If low[start:] begins with an alias, return (alias, canon, end_index)."""
    chunk = low[start:]
    for alias, canon in HEADER_ALIASES:
        if alias == "project":
            if chunk == "project" or chunk.startswith("project:") or chunk.startswith("project "):
                # only exact token "project", not "projects" (handled by longer alias)
                if chunk.startswith("projects"):
                    continue
                end = start + len("project")
                return alias, canon, end
            continue
        if chunk == alias:
            return alias, canon, start + len(alias)
        if chunk.startswith(alias):
            end = start + len(alias)
            if end < len(low) and low[end] not in " &/|:-–." and not low[end].isspace():
                continue
            return alias, canon, end
    return None


def _match_section_header(line: str) -> tuple[str, str] | None:
    """
    If line is / starts with a known section header, return (canonical, remainder).
    Allows glued PDF lines like 'PROJECTS Smart Home System'.
    """
    norm = _prep_header_line(line)
    if not norm or len(norm) > 120:
        return None
    low_exact = norm.lower().strip(" :.-–|/&")
    low = norm.lower()

    for alias, canon in HEADER_ALIASES:
        if low_exact == alias:
            return canon, ""

    for alias, canon in HEADER_ALIASES:
        if alias == "project":
            if low_exact == "project":
                return canon, ""
            continue
        if not low.startswith(alias):
            continue
        if len(low) == len(alias):
            return canon, ""
        next_ch = low[len(alias)]
        rest = norm[len(alias) :].strip()
        if next_ch in "&/|:-–.":
            rest = rest.lstrip(" &/|:-–.")
            if not rest or len(rest.split()) <= 14:
                return canon, rest
            continue
        if next_ch.isspace() and canon == "projects":
            rest_clean = rest.lstrip(" &/|:-–.")
            if rest_clean.lower() in {
                "research",
                "portfolio",
                "work",
                "overview",
                "and research",
            }:
                return canon, ""
            # Side-by-side column headers: "PROJECTS EXPERIENCE" handled elsewhere
            if _match_alias_at(rest_clean.lower()) and len(rest_clean.split()) <= 4:
                return canon, ""
            if len(rest_clean.split()) <= 14 and not re.match(
                r"(?i)^(with|in|of|at|as|for|include|including)\b", rest_clean
            ):
                return canon, rest_clean
    return None


def _split_side_by_side_headers(line: str) -> list[tuple[str, str]] | None:
    """
    Detect two-column header lines like 'EXPERIENCE PROJECTS' or 'SKILLS LANGUAGES'.
    Returns list of (canon, '') if the line is only headers.
    """
    norm = _prep_header_line(line)
    if not norm or len(norm.split()) > 6:
        return None
    low = norm.lower().strip(" :.-–|/&")
    found: list[str] = []
    i = 0
    while i < len(low):
        while i < len(low) and low[i] in " &/|:-–.":
            i += 1
        if i >= len(low):
            break
        hit = _match_alias_at(low, i)
        if not hit:
            return None
        alias, canon, end = hit
        found.append(canon)
        i = end
    if len(found) >= 2:
        return [(c, "") for c in found]
    return None


def _is_tech_tag_line(line: str) -> bool:
    """Single-token stack tags like 'LangChain.' or pure tech lists."""
    s = line.strip()
    if TECH_ONLY.match(s.rstrip(".")):
        return True
    core = s.rstrip(".")
    parts = core.split()
    if len(parts) != 1:
        return False
    tok = parts[0]
    if not re.match(r"^[A-Za-z][A-Za-z0-9+.#/-]*$", tok):
        return False
    if tok.lower() in {
        "langchain",
        "python",
        "javascript",
        "typescript",
        "react",
        "nodejs",
        "docker",
        "kubernetes",
        "pytorch",
        "tensorflow",
    }:
        return True
    # CamelCase library-style token
    if any(c.islower() for c in tok[1:]) and any(c.isupper() for c in tok[1:]):
        return True
    if tok.isupper() and len(tok) <= 8:
        return True
    return False


def _is_description_line(line: str) -> bool:
    """True for bullets/tech that must never become project titles."""
    if not line:
        return True
    if line[:1].islower():
        return True
    if ACTION_START.match(line):
        return True
    core = line.rstrip(".")
    if _is_tech_tag_line(core) or _is_tech_tag_line(line):
        return True
    # Trailing period: reject sentence-like lines; keep short title names
    if line.endswith("."):
        words = core.split()
        if len(words) >= 2 and len(words) <= 8 and not ACTION_START.match(core):
            return False
        return True
    return False


def _words_to_lines(words: list[dict[str, Any]], y_tol: float = 3.0) -> str:
    if not words:
        return ""
    ordered = sorted(words, key=lambda w: (round(float(w["top"]) / y_tol), float(w["x0"])))
    lines: list[str] = []
    cur_y: float | None = None
    cur: list[str] = []
    for w in ordered:
        top = float(w["top"])
        if cur_y is None or abs(top - cur_y) <= y_tol:
            cur.append(w["text"])
            cur_y = top if cur_y is None else cur_y
        else:
            lines.append(" ".join(cur))
            cur = [w["text"]]
            cur_y = top
    if cur:
        lines.append(" ".join(cur))
    return "\n".join(lines)


def _page_text_prefer_columns(page: Any) -> str:
    """
    For typical two-column CVs, read left column then right so section headers
    stay contiguous instead of 'EXPERIENCE PROJECTS' on one interleaved line.
    """
    try:
        words = page.extract_words() or []
    except Exception:
        words = []
    plain = page.extract_text() or ""
    if len(words) < 25:
        return plain

    width = float(getattr(page, "width", 0) or 0) or 1.0
    mid = width * 0.5
    left = [w for w in words if (float(w["x0"]) + float(w["x1"])) / 2 < mid]
    right = [w for w in words if (float(w["x0"]) + float(w["x1"])) / 2 >= mid]
    if len(left) < 10 or len(right) < 10:
        return plain

    # Require both columns to span a decent vertical range (true 2-col, not sparse)
    left_span = max(float(w["top"]) for w in left) - min(float(w["top"]) for w in left)
    right_span = max(float(w["top"]) for w in right) - min(float(w["top"]) for w in right)
    if left_span < 40 or right_span < 40:
        return plain

    col_text = _words_to_lines(left) + "\n" + _words_to_lines(right)
    # Prefer column reading when it surfaces more recognizable section headers
    plain_hits = sum(1 for ln in plain.splitlines() if _match_section_header(ln))
    col_hits = sum(1 for ln in col_text.splitlines() if _match_section_header(ln))
    if col_hits >= plain_hits:
        return col_text
    return plain


class CVAnalyzer:
    def __init__(self):
        self.taxonomy = load_taxonomy()
        self.extractor = JobExtractor(self.taxonomy)

    def extract_text_from_pdf(self, data: bytes) -> str:
        import pdfplumber

        texts = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                texts.append(_page_text_prefer_columns(page))
        return "\n".join(texts)

    def extract_text_from_docx(self, data: bytes) -> str:
        from docx import Document

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        try:
            doc = Document(str(tmp_path))
            return "\n".join(p.text for p in doc.paragraphs)
        finally:
            tmp_path.unlink(missing_ok=True)

    def extract_text(self, filename: str, data: bytes) -> str:
        lower = filename.lower()
        if lower.endswith(".pdf"):
            return self.extract_text_from_pdf(data)
        if lower.endswith(".docx"):
            return self.extract_text_from_docx(data)
        return data.decode("utf-8", errors="ignore")

    def _sections(self, text: str) -> dict[str, str]:
        """Line-based split into known sections; no whole-CV project fallback."""
        sections: dict[str, str] = {}
        current: str | None = None
        body_lines: list[str] = []
        buckets: dict[str, list[str]] = {}

        for raw in (text or "").splitlines():
            multi = _split_side_by_side_headers(raw)
            if multi:
                for canon, _rem in multi:
                    current = canon
                    buckets.setdefault(canon, [])
                continue
            hit = _match_section_header(raw)
            if hit:
                canon, remainder = hit
                current = canon
                buckets.setdefault(canon, [])
                if remainder:
                    buckets[canon].append(remainder)
                continue
            if current is None:
                body_lines.append(raw)
            else:
                buckets.setdefault(current, []).append(raw)

        if body_lines:
            sections["body"] = "\n".join(body_lines).strip()
        for canon, lines in buckets.items():
            sections[canon] = "\n".join(lines).strip()
        return sections

    def _title_candidate(self, line: str) -> str | None:
        cleaned = LEADING_DECOR.sub("", line).strip()
        cleaned = re.sub(r"(?i)^project\s*[:\-–]\s*", "", cleaned).strip()
        if not cleaned:
            return None
        # Prefer left side of Title — description / Title: description
        parts = TITLE_SPLIT.split(cleaned, maxsplit=1)
        if len(parts) == 2:
            left = parts[0].strip()
            if self._is_project_title(left) and not _is_description_line(left):
                return left
            return None
        if _is_description_line(cleaned):
            return None
        if not self._is_project_title(cleaned):
            return None
        return cleaned

    def _is_project_title(self, line: str) -> bool:
        """Strict noun-phrase titles only (main idea), not bullets or sentences."""
        if not line or len(line) < 3 or len(line) > 100:
            return False
        low = line.lower().strip()
        if low in {"projects", "project", "experience", "education", "skills"}:
            return False
        if re.match(r"(?i)^(email|phone|linkedin|http|www\.)", line):
            return False
        if _is_description_line(line):
            return False
        if not line[:1].isupper():
            return False
        words = line.split()
        # Main idea: short name, not a sentence
        if len(words) > 10:
            return False
        # Avoid comma-heavy skill/algorithm lists masquerading as titles
        if line.count(",") >= 2:
            return False
        # PDF wrap continuations often end mid-phrase
        if re.search(
            r"(?i)\b(and|or|with|of|the|a|an|for|to|in|on|by|from|using)$",
            line.rstrip(".,;:"),
        ):
            return False
        return True

    def _extract_project_titles(self, projects_blob: str) -> list[str]:
        """Titles only from the Projects section body — no whole-CV fallback."""
        if not (projects_blob or "").strip():
            return []

        titles: list[str] = []
        for raw in projects_blob.splitlines():
            ln = _normalize_line(raw)
            if not ln:
                continue
            cand = self._title_candidate(ln)
            if cand:
                titles.append(cand)

        seen: set[str] = set()
        out: list[str] = []
        for t in titles:
            key = t.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(t)
            if len(out) >= 12:
                break
        return out

    def _project_hint_lines(self, text: str) -> list[str]:
        hints: list[str] = []
        for raw in (text or "").splitlines():
            ln = _normalize_line(raw)
            if not ln:
                continue
            if re.search(r"(?i)\bprojects?\b|\bportfolio\b|\bcapstone\b", ln):
                hints.append(ln[:160])
            if len(hints) >= 8:
                break
        return hints

    def analyze_text(self, text: str) -> dict[str, Any]:
        sections = self._sections(text)
        skills_blob = " ".join(
            [
                sections.get("skills", ""),
                sections.get("projects", ""),
                sections.get("experience", ""),
                sections.get("body", ""),
                text,
            ]
        )
        extracted = self.extractor.extract_skills(skills_blob)
        skill_names = [s["name"] for s in extracted]
        edu_section = sections.get("education") or ""
        edu = self.extractor.extract_education(edu_section or text)
        # Major is often outside a short Education blob (or PDF-split); fall back to full CV
        if not (edu.get("education_fields") or []):
            edu_full = self.extractor.extract_education(text)
            edu["education_fields"] = edu_full.get("education_fields") or []
            if not edu.get("education_level"):
                edu["education_level"] = edu_full.get("education_level")
        languages = self.extractor.extract_languages(text)
        exp_level = self.extractor.extract_experience_level(text)
        internships = len(re.findall(r"(?i)\bintern(ship)?\b", text))
        certs = []
        if "certifications" in sections:
            certs = [
                line.strip("-• \t")
                for line in sections["certifications"].splitlines()
                if line.strip()
            ][:20]

        projects_section_found = "projects" in sections
        projects = (
            self._extract_project_titles(sections.get("projects") or "")
            if projects_section_found
            else []
        )

        order = [
            "summary",
            "education",
            "experience",
            "projects",
            "skills",
            "certifications",
            "languages",
        ]
        detected_sections = [s for s in order if s in sections]
        hints = [] if projects_section_found else self._project_hint_lines(text)

        targets = list(edu.get("education_fields") or [])
        return {
            "skills": skill_names,
            "skills_structured": extracted,
            "education_level": edu.get("education_level"),
            "education_fields": edu.get("education_fields") or [],
            "experience_level": exp_level or ("Internship" if internships else None),
            "internship_mentions": internships,
            "languages": languages,
            "certifications": certs,
            "projects": projects,
            "projects_section_found": projects_section_found,
            "detected_sections": detected_sections,
            "project_hint_lines": hints,
            "target_categories": targets,
            "summary": (sections.get("summary") or "")[:500],
            "privacy_note": (
                "CV files are processed ephemerally and are not permanently stored by default."
            ),
        }

    def analyze_file(self, filename: str, data: bytes) -> dict[str, Any]:
        text = self.extract_text(filename, data)
        profile = self.analyze_text(text)
        profile["raw_text_length"] = len(text)
        profile["filename"] = filename
        return profile
