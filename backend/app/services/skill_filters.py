"""Shared technical / category skill filters for Coach and Skill Gap."""

from __future__ import annotations

from typing import Any

SOFT_PARENTS = {"business_soft_skills", "business___soft_skills", "languages"}

CATEGORY_FALLBACK = {
    "Computer Engineering": "Software Engineering",
}


def canonical_category(category: str | None) -> str | None:
    if not category:
        return category
    return CATEGORY_FALLBACK.get(category, category)

SOFTWARE_CATS = {
    "Software Engineering",
    "Web Development",
    "Data Science",
    "Artificial Intelligence",
    "Cybersecurity",
}
SOFTWARE_SKILL_ROOTS = {
    "programming",
    "web_development",
    "data",
    "ai___machine_learning",
    "cloud___devops",
    "cybersecurity",
}
MECH_CATS = {"Mechanical Engineering", "Mechatronics Engineering"}
MECH_SKILL_ROOTS = {
    "mechanical_engineering",
    "mechatronics___robotics",
    "industrial_automation",
}
ELEC_CATS = {
    "Electrical Engineering",
    "Electronics Engineering",
    "Automation Engineering",
    "Robotics",
}
ELEC_SKILL_ROOTS = {
    "electrical_engineering",
    "mechatronics___robotics",
    "industrial_automation",
}
CIVIL_CATS = {"Civil Engineering", "Architecture"}
CIVIL_SKILL_ROOTS = {"civil___architecture", "mechanical_engineering"}

# Degree / education field strings → job categories used in matching.
DEGREE_TO_CATEGORY = {
    "computer science": "Software Engineering",
    "computer engineering": "Software Engineering",
    "cce": "Software Engineering",
    "informatics": "Software Engineering",
    "information technology": "Software Engineering",
    "software engineering": "Software Engineering",
    "web development": "Web Development",
    "data science": "Data Science",
    "artificial intelligence": "Artificial Intelligence",
    "cybersecurity": "Cybersecurity",
    "electrical engineering": "Electrical Engineering",
    "electronics engineering": "Electronics Engineering",
    "mechanical engineering": "Mechanical Engineering",
    "mechatronics engineering": "Mechatronics Engineering",
    "automation engineering": "Automation Engineering",
    "robotics": "Robotics",
    "civil engineering": "Civil Engineering",
    "architecture": "Architecture",
}


def education_field_to_category(field: str | None) -> str | None:
    if not field or not str(field).strip():
        return None
    mapped = canonical_category(str(field).strip()) or str(field).strip()
    return DEGREE_TO_CATEGORY.get(mapped.lower(), mapped)

SOFT_NAMES = {
    "communication",
    "leadership",
    "teamwork",
    "english",
    "arabic",
    "french",
    "problem solving",
}


def root_parent(taxonomy: Any, skill_id: str) -> str | None:
    sid = skill_id
    seen: set[str] = set()
    last = sid
    while sid and sid not in seen:
        seen.add(sid)
        last = sid
        parent = (taxonomy.skills.get(sid) or {}).get("parent_id")
        if not parent:
            return last
        sid = parent
    return last


def is_technical(taxonomy: Any, skill_id: str) -> bool:
    meta = taxonomy.skills.get(skill_id) or {}
    root = root_parent(taxonomy, skill_id)
    if root in SOFT_PARENTS or skill_id in SOFT_PARENTS:
        return False
    parent = meta.get("parent_id")
    if parent in SOFT_PARENTS:
        return False
    name = (meta.get("name") or skill_id).lower()
    if name in SOFT_NAMES:
        return False
    return True


def skill_fits_category(taxonomy: Any, skill_id: str, category: str) -> bool:
    if not is_technical(taxonomy, skill_id):
        return False
    root = root_parent(taxonomy, skill_id)
    if category in SOFTWARE_CATS:
        return root in SOFTWARE_SKILL_ROOTS
    if category in MECH_CATS:
        return root in MECH_SKILL_ROOTS or skill_id in {"matlab", "python", "c", "cplusplus"}
    if category in ELEC_CATS:
        return root in ELEC_SKILL_ROOTS or skill_id in {"matlab", "python", "c", "cplusplus"}
    if category in CIVIL_CATS:
        return root in CIVIL_SKILL_ROOTS
    return True
