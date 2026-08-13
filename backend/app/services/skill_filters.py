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
MECH_SKILL_ROOTS = {"mechanical_engineering", "mechatronics", "industrial_automation"}
ELEC_CATS = {
    "Electrical Engineering",
    "Electronics Engineering",
    "Automation Engineering",
    "Robotics",
}
ELEC_SKILL_ROOTS = {
    "electrical_engineering",
    "electronics",
    "industrial_automation",
    "mechatronics",
}
CIVIL_CATS = {"Civil Engineering", "Architecture"}
CIVIL_SKILL_ROOTS = {"civil_engineering", "architecture", "mechanical_engineering"}

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
