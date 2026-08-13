from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


class SkillTaxonomy:
    """Hierarchical skill taxonomy with alias normalization."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        self.categories: dict[str, Any] = raw.get("categories", {})
        self.skills: dict[str, dict[str, Any]] = {}
        self.alias_to_id: dict[str, str] = {}
        self._flatten(self.categories, parent_id=None, subcategory=None)
        # abbreviation map for cleaning
        self.abbreviations: dict[str, str] = {
            k.lower(): v for k, v in (raw.get("abbreviations") or {}).items()
        }

    def _flatten(
        self,
        node: dict[str, Any],
        parent_id: str | None,
        subcategory: str | None,
    ) -> None:
        for key, value in node.items():
            skill_id = self._slug(key)
            aliases = []
            children = {}
            if isinstance(value, dict):
                aliases = list(value.get("aliases") or [])
                children = {k: v for k, v in value.items() if k != "aliases"}
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        children[item] = {}
                    elif isinstance(item, dict):
                        children.update(item)
            self.skills[skill_id] = {
                "skill_id": skill_id,
                "name": key,
                "parent_id": parent_id,
                "subcategory": subcategory or parent_id,
                "aliases": aliases,
            }
            # Soft skills: only register multi-word forms / explicit aliases to
            # avoid false positives (e.g. "communication" in "industrial communication").
            soft_parents = {"business_soft_skills", "business___soft_skills"}
            is_soft = parent_id in soft_parents or skill_id in soft_parents
            # Always register canonical name; soft-skill false positives are
            # filtered in the extractor for known technical phrases.
            self._register_alias(key, skill_id)
            for a in aliases:
                self._register_alias(a, skill_id)
            if children:
                self._flatten(children, parent_id=skill_id, subcategory=key)

    def _register_alias(self, text: str, skill_id: str) -> None:
        norm = self.normalize_text(text)
        if norm:
            self.alias_to_id[norm] = skill_id

    @staticmethod
    def _slug(text: str) -> str:
        return (
            text.strip()
            .lower()
            .replace("/", "_")
            .replace("&", "and")
            .replace(" ", "_")
            .replace("-", "_")
            .replace(".", "")
            .replace("+", "plus")
            .replace("#", "sharp")
        )

    @staticmethod
    def normalize_text(text: str) -> str:
        return " ".join(text.lower().strip().split())

    def canonical_id(self, text: str) -> str | None:
        return self.alias_to_id.get(self.normalize_text(text))

    def canonical_name(self, text: str) -> str | None:
        sid = self.canonical_id(text)
        if not sid:
            return None
        return self.skills[sid]["name"]

    def related_ids(self, skill_id: str) -> set[str]:
        """Parent, self, and sibling/children IDs for soft relatedness."""
        if skill_id not in self.skills:
            return set()
        related = {skill_id}
        parent = self.skills[skill_id].get("parent_id")
        if parent:
            related.add(parent)
            for sid, meta in self.skills.items():
                if meta.get("parent_id") == parent:
                    related.add(sid)
        for sid, meta in self.skills.items():
            if meta.get("parent_id") == skill_id:
                related.add(sid)
        return related

    def all_alias_patterns(self) -> list[tuple[str, str]]:
        """Longest-first alias patterns for dictionary matching."""
        items = sorted(self.alias_to_id.items(), key=lambda x: len(x[0]), reverse=True)
        return items


@lru_cache(maxsize=1)
def load_taxonomy(path: str = "data_pipeline/taxonomy/skills.yaml") -> SkillTaxonomy:
    return SkillTaxonomy(path)
