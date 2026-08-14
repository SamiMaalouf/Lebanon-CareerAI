from types import SimpleNamespace

from backend.app.services.matching import MatchingEngine


def _job(skills: list[tuple[str, bool]], title: str = "Role", category: str = "Software Engineering"):
    return SimpleNamespace(
        job_id="j1",
        job_title=title,
        company="Acme",
        location="Beirut",
        job_category=category,
        education_level="Bachelor's",
        experience_level="Internship",
        embedding=None,
        cleaned_text="",
        description="",
        requirements="",
        skills=[SimpleNamespace(skill_id=sid, is_required=req) for sid, req in skills],
    )


def test_keyword_ignores_language_and_teamwork_overlap():
    engine = MatchingEngine()
    candidate = {
        "skills": ["English", "Arabic", "Teamwork", "Communication", "Python"],
        "education_level": "Bachelor's",
        "experience_level": "Internship",
        "target_categories": ["Software Engineering"],
    }
    language_only = _job([("english", True), ("teamwork", True), ("communication", True)])
    kw = engine.keyword_score(candidate, language_only)
    assert kw["matched_skills"] == []
    assert kw["compatibility_score"] == 0
    assert kw["listed_count"] == 0

    with_python = _job([("english", True), ("teamwork", True), ("python", True)])
    kw2 = engine.keyword_score(candidate, with_python)
    names = {n.lower() for n in kw2["matched_skills"]}
    assert names == {"python"}
    assert kw2["matched_count"] == 1
    assert kw2["listed_count"] == 1
    assert "english" not in names
    assert "teamwork" not in names
    assert kw2["compatibility_score"] > 0


def test_semantic_does_not_credit_soft_skill_only_jobs():
    engine = MatchingEngine()
    candidate = {
        "skills": ["English", "French", "Teamwork", "Python"],
        "education_level": "Bachelor's",
        "education_fields": ["Software Engineering"],
        "experience_level": "Internship",
        "target_categories": ["Software Engineering"],
    }
    job = _job([("english", True), ("french", True), ("teamwork", True)])
    sem = engine.semantic_score(candidate, job)
    assert sem["matched_skills"] == []
    assert sem["has_technical_overlap"] is False
    assert sem["components"]["required_coverage"] == 0
    assert sem["compatibility_score"] < 40
