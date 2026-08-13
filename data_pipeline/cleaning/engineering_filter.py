"""Engineering / engineering-internship gate and rule-based categories."""

from __future__ import annotations

import re
from typing import Any

ENGINEERING_CATEGORIES = [
    "Software Engineering",
    "Web Development",
    "Data Science",
    "Artificial Intelligence",
    "Cybersecurity",
    "Electrical Engineering",
    "Electronics Engineering",
    "Mechanical Engineering",
    "Mechatronics Engineering",
    "Automation Engineering",
    "Robotics",
    "Civil Engineering",
    "Architecture",
]

# Ordered most-specific first
CATEGORY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)\belectromechanical|mechatronic"), "Mechatronics Engineering"),
    (re.compile(r"(?i)\brobotic|\bros\b|robot\b"), "Robotics"),
    (re.compile(r"(?i)\bautomation|\bplc\b|\bscada\b|\bhmi\b|industrial control"), "Automation Engineering"),
    (
        re.compile(
            r"(?i)\b(artificial intelligence|\bai engineer|\bai/ml|machine learning|"
            r"deep learning|computer vision|\bnlp\b|llm engineer|generative ai)\b"
        ),
        "Artificial Intelligence",
    ),
    (
        re.compile(r"(?i)\b(data scien|data engineer|data analyst|business intelligence|\bbi\b|etl)\b"),
        "Data Science",
    ),
    (
        re.compile(
            r"(?i)\b(cyber.?sec|information security|infosec|penetration|appsec|"
            r"soc analyst|security engineer)\b"
        ),
        "Cybersecurity",
    ),
    (
        re.compile(
            r"(?i)\b(front.?end|back.?end|full.?stack|web develop|react|angular|vue\.?js|"
            r"next\.?js|laravel|wordpress developer)\b"
        ),
        "Web Development",
    ),
    (
        re.compile(
            r"(?i)\bcomputer\s*(?:and|&)?\s*communications?\s*engineering|"
            r"\bcomputer\s*engineering\b|\bcomp\.?\s*eng\.?\b|\bcce\b|"
            r"\bembedded (software|systems?|engineer|developer|linux)|"
            r"\bfirmware\b|\bfpga\b|\bvhdl\b|\bverilog\b|"
            r"\bhardware (engineer|design|developer)\b|"
            r"\bmicrocontroller|\biot engineer\b|"
            r"\b(software|developer|programmer|devops|sre|site reliability|"
            r"mobile (developer|engineer)|android|ios engineer|qa engineer|sdet)\b"
        ),
        "Software Engineering",
    ),
    (re.compile(r"(?i)\belectronic"), "Electronics Engineering"),
    (re.compile(r"(?i)\belectrical|\bpower (system|engineer)|hv/lv|\bhvac control"), "Electrical Engineering"),
    (
        re.compile(
            r"(?i)\bmechanical|\bcad\b|\bsolidworks\b|\bcnc\b|hvac engineer|piping engineer|"
            r"thermal engineer"
        ),
        "Mechanical Engineering",
    ),
    (
        re.compile(
            r"(?i)\bcivil|\bstructural engineer|\bsite engineer|\bqc engineer|"
            r"quantity survey|\brevit\b|\bbim\b"
        ),
        "Civil Engineering",
    ),
    (re.compile(r"(?i)\barchitect(ure)?\b|urban design|bim architect"), "Architecture"),
]

# Strong title/body allow signals (STEM/engineering)
ALLOW_TITLE = re.compile(
    r"(?i)\b("
    r"engineer|engineering|developer|programmer|devops|sre|"
    r"mechatronic|mechanical|electrical|electronic|electromechanical|civil|structural|"
    r"automation|robotic|embedded|firmware|\bplc\b|scada|"
    r"data scien|data engineer|machine learning|deep learning|"
    r"cyber.?sec|infosec|full.?stack|front.?end|back.?end|"
    r"architect(ure|ural)?|\bbim\b|revit|autocad|solidworks|"
    r"network engineer|systems engineer|qa engineer|sdet|"
    r"computer (science|engineer)|telecom|rf engineer|"
    r"it intern|tech intern|technical intern|"
    r"industrial engineer|petroleum engineer|chemical engineer|"
    r"hardware|iot\b|fpga|vhdl|verilog|software|"
    r"mobile (developer|engineer)|android developer|ios developer|"
    r"web developer|site engineer|qc engineer|drafts(man|person)|cad\b|"
    r"\bai engineer|\bai/ml|"
    r"(electro)?mechanical technician|electrical technician|automation technician|"
    r"architectural (designer|drafter|intern)"
    r")\b"
)

ALLOW_BODY_STRONG = re.compile(
    r"(?i)\b("
    r"bachelor.{0,40}(engineering|computer science|mechatronic|mechanical|electrical|civil)|"
    r"degree in (engineering|computer|mechatronic|mechanical|electrical|civil|software)|"
    r"software engineer|mechanical engineer|electrical engineer|civil engineer|"
    r"mechatronics|embedded systems|plc programming|scada|"
    r"full.?stack developer|backend developer|frontend developer|"
    r"machine learning engineer|data scientist|devops engineer"
    r")\b"
)

# Roles that should never pass even if "engineer" appears in boilerplate
DENY_TITLE = re.compile(
    r"(?i)\b("
    r"sales(?!\s+engineer)|account executive|business development|bdm\b|marketing|"
    r"social media|content creator|copywriter|recruiter|talent acquisition|"
    r"human resources|\bhr\b|nurse|doctor|pharmacist|chef|waiter|barista|"
    r"cashier|receptionist|hotel|travel consultant|driver|"
    r"accountant|bookkeep|auditor|lawyer|attorney|finance|financial|"
    r"customer (care|service|support|success)(?!\s*engineer)|call center|"
    r"content (creator|creation)|video content|"
    r"graphic designer|makeup|beautician|fitness|instructor|teacher|"
    r"virtual assistant|administrative|secretary|coordinator(?!\s+engineer)|"
    r"creative manager|brand |campaign |hostess|waiter|nurse|"
    r"medical|dental|pharmacy|sales person|sales associate|indoor sales|"
    r"tutor|teacher|instructor|officer(?!\s+engineer)|panel support"
    r")\b"
)

INTERNSHIP_PATTERN = re.compile(
    r"(?i)(?<![\w-])(intern(?:ship)?|stagiaire|trainee)(?![\w-])"
)
# French "stage" only in titles — English body text uses "stage" for project phases
INTERNSHIP_TITLE_STAGE = re.compile(r"(?i)(?<![\w-])stage(?![\w-])")


def is_internship(title: str = "", text: str = "") -> bool:
    title = title or ""
    if INTERNSHIP_PATTERN.search(title) or INTERNSHIP_TITLE_STAGE.search(title):
        return True
    return bool(INTERNSHIP_PATTERN.search((text or "")[:1500]))


CE_BODY_ROLE = re.compile(
    r"(?i)\bembedded (software|systems?|engineer|developer|linux)|"
    r"\bfirmware\b|\bfpga\b|\bvhdl\b|\bverilog\b|"
    r"\bhardware (engineer|design|developer)\b|"
    r"\bmicrocontroller|\biot engineer\b"
)
CE_DEGREE = re.compile(
    r"(?i)(?:bachelor'?s?|degree in|b\.?e\.?|b\.?eng).{0,60}"
    r"(computer\s*(?:and|&)?\s*communications?\s*engineering|"
    r"computer\s*engineering|\bcce\b)"
)
OTHER_MAJORS = re.compile(
    r"(?i)\b(civil|mechanical|electrical|software engineering|computer science|architecture)\b"
)
GRAD_IT_TITLE = re.compile(
    r"(?i)fresh|graduate|it graduate|engineering\s*(?:and|&)\s*it|dual nationality"
)
CE_LEAD_MAJORS = re.compile(
    r"(?i)(?:fresh|graduate|degree|bachelor|hire).{0,120}"
    r"(computer engineering|\bcce\b|computer and communications)"
)


def targets_ce_graduates(title: str = "", text: str = "") -> bool:
    """True when the ad specifically asks for Computer Engineering / CCE graduates."""
    title = title or ""
    blob = f"{title}\n{(text or '')[:4000]}"
    for match in CE_DEGREE.finditer(blob):
        window = blob[max(0, match.start() - 40) : match.end() + 50]
        if not OTHER_MAJORS.search(window):
            return True
    if GRAD_IT_TITLE.search(title) and CE_LEAD_MAJORS.search(blob):
        return True
    return False


def classify_engineering_category(title: str = "", text: str = "") -> tuple[str, float]:
    """Return (category, confidence) using ordered rules. Prefer title matches."""
    title = title or ""
    text = text or ""
    for pat, label in CATEGORY_RULES:
        if pat.search(title):
            return label, 0.92

    if targets_ce_graduates(title, text):
        return "Software Engineering", 0.78

    blob = f"{title}\n{text[:4000]}"
    for pat, label in CATEGORY_RULES:
        if pat.search(blob):
            return label, 0.68

    return "Other", 0.0


def is_engineering_role(title: str = "", description: str = "", requirements: str = "") -> tuple[bool, str]:
    """Gate: keep STEM/engineering (+ eng internships). Reject sales/marketing/etc."""
    title = (title or "").strip()
    desc = description or ""
    reqs = requirements or ""
    blob = f"{title}\n{desc[:2500]}\n{reqs[:1000]}"

    if not title:
        return False, "missing_title"

    if DENY_TITLE.search(title):
        # Title STEM signal wins over soft deny tokens (e.g. Sales Engineer)
        if not ALLOW_TITLE.search(title):
            return False, "deny_title"

    if ALLOW_TITLE.search(title):
        return True, "title_allow"

    # Internships: engineering signal must be in the title, not buried in
    # generic "we use software" job-ad boilerplate.
    if is_internship(title, blob):
        return False, "non_eng_internship"

    # Body-only: title must look technical AND body has a strong eng phrase
    if ALLOW_BODY_STRONG.search(blob) and re.search(
        r"(?i)\b(tech|technical|it\b|digital|computer|system|design|product|"
        r"operations|infrastructure|r&d|research)\b",
        title,
    ):
        return True, "body_allow"

    return False, "no_eng_signal"


def annotate_engineering(record: dict[str, Any]) -> dict[str, Any] | None:
    """
    Return enriched record if it passes the engineering gate, else None.
    Sets job_category (rule), category_confidence, is_internship.
    """
    title = record.get("job_title") or ""
    desc = record.get("description") or record.get("cleaned_text") or ""
    reqs = record.get("requirements") or ""
    ok, reason = is_engineering_role(title, desc, reqs)
    if not ok:
        return None

    cat, conf = classify_engineering_category(title, f"{desc}\n{reqs}")
    out = dict(record)
    out["is_internship"] = is_internship(title, f"{desc}\n{reqs}")
    if out["is_internship"] and not out.get("experience_level"):
        out["experience_level"] = "Internship"
    # Always re-apply rule labels so stale Software Engineering tags get fixed
    out["job_category"] = cat
    out["category_confidence"] = conf
    out["engineering_gate_reason"] = reason
    return out


def filter_engineering_jobs(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    kept: list[dict[str, Any]] = []
    reasons: dict[str, int] = {}
    for r in records:
        title = r.get("job_title") or ""
        desc = r.get("description") or r.get("cleaned_text") or ""
        reqs = r.get("requirements") or ""
        ok, reason = is_engineering_role(title, desc, reqs)
        if not ok:
            reasons[reason] = reasons.get(reason, 0) + 1
            continue
        annotated = annotate_engineering(r)
        if annotated is None:
            reasons["annotate_drop"] = reasons.get("annotate_drop", 0) + 1
            continue
        kept.append(annotated)
        reasons["kept"] = reasons.get("kept", 0) + 1
        if annotated.get("is_internship"):
            reasons["internships"] = reasons.get("internships", 0) + 1
    return kept, reasons
