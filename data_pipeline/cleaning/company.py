"""Drop HireLebanese chrome and other placeholder employer names."""

from __future__ import annotations

import re

# Exact / whole-string junk (after strip)
PLACEHOLDER_EXACT = re.compile(
    r"(?i)^\s*("
    r"n/?a|n\.a\.|none|null|unknown|undisclosed|"
    r"confidential(ly)?(\s*\d+)?|"
    r"not specified|not available|not listed|"
    r"apply now|click here|sign up|sign in|log ?in|"
    r"candidate sign.?up|employer sign.?up|"
    r"company|company name|the company|"
    r"private|private company|"
    r"hirelebanese|jobs ?for ?lebanon|jobslebanon|"
    r"energy jobline( zr)?|"
    r"tbd|to be (announced|confirmed)|"
    r"—+|-+|\.+"
    r")\s*$"
)

# Site chrome that sometimes lands in the Company field
PLACEHOLDER_FRAGMENT = re.compile(
    r"(?i)("
    r"candidate sign.?up|employer sign.?up|"
    r"sign up to (apply|view)|click to apply|"
    r"privacy policy|cookie policy|toggle navigation"
    r")"
)


def is_placeholder_company(name: str | None) -> bool:
    if name is None:
        return True
    value = str(name).strip()
    if len(value) < 2:
        return True
    if PLACEHOLDER_EXACT.match(value):
        return True
    if PLACEHOLDER_FRAGMENT.search(value):
        return True
    return False


def clean_company(name: str | None) -> str | None:
    if is_placeholder_company(name):
        return None
    return str(name).strip()[:512]


_CHROME_LINE = re.compile(
    r"(?i)^(job description|company description|about the role|what you.?ll do|"
    r"key responsibilities|i.?m interested|search all jobs|full-time|part-time|"
    r"remote:|mid-senior|entry level|information technology|engineering)$"
)
_IS_A = re.compile(
    r"^(.{2,90}?)\s+(?:is|are|has been|was)\s+(?:a|an|the|our)\b",
    re.I,
)


def infer_company_from_text(text: str | None) -> str | None:
    """Pull a real employer name from HireLebanese 'Company Description' copy."""
    if not text:
        return None
    match = re.search(r"(?i)company description\s*\n+([^\n]{2,160})", text)
    if not match:
        return None
    line = match.group(1).strip()
    if _CHROME_LINE.match(line):
        return None
    named = _IS_A.match(line)
    candidate = named.group(1).strip() if named else line.split(".")[0].strip()
    candidate = re.sub(r"\s+(IT Department|department|team)$", "", candidate, flags=re.I)
    cleaned = clean_company(candidate)
    if not cleaned:
        return None
    if len(cleaned.split()) > 10:
        return None
    return cleaned


def resolve_company(name: str | None, text: str | None = None) -> str | None:
    return clean_company(name) or infer_company_from_text(text)
