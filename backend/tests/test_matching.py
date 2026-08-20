from types import SimpleNamespace

from backend.app.services.matching import MatchingEngine


def _job(
    skills: list[tuple[str, bool]],
    title: str = "Role",
    category: str = "Software Engineering",
    *,
    is_internship: bool = False,
    experience_level: str | None = "Internship",
):
    return SimpleNamespace(
        job_id="j1",
        job_title=title,
        company="Acme",
        location="Beirut",
        job_category=category,
        education_level="Bachelor's",
        experience_level=experience_level,
        is_internship=is_internship,
        source_url="https://example.local/job",
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


def test_missing_skills_lists_unmatched_tools():
    engine = MatchingEngine()
    job = _job([("python", True), ("docker", True), ("kubernetes", True)])
    kw = engine.keyword_score({"skills": ["Python"], "experience_level": "Internship"}, job)
    missing = {n.lower() for n in kw["missing_skills"]}
    assert "docker" in missing
    assert "kubernetes" in missing
    assert "python" not in missing


def test_senior_role_is_stretch_learn_for_junior():
    engine = MatchingEngine()
    candidate = {"skills": ["Python"], "experience_level": "Internship"}
    job = _job(
        [("python", True)],
        title="Senior Full-Stack / Product Engineer",
        is_internship=False,
        experience_level="5+ years",
    )
    row = engine.annotate_match(candidate, job, engine.keyword_score(candidate, job))
    assert row["seniority"] == "stretch"
    assert row["band"] == "learn"


def test_intern_sql_one_of_one_is_apply():
    engine = MatchingEngine()
    candidate = {"skills": ["SQL", "Python"], "experience_level": "Internship"}
    job = _job(
        [("sql", True)],
        title="Software Support Intern",
        is_internship=True,
        experience_level="Internship",
    )
    row = engine.annotate_match(candidate, job, engine.keyword_score(candidate, job))
    assert row["is_internship"] is True
    assert row["seniority"] == "fit"
    assert row["band"] == "apply"
    assert row["matched_count"] == 1
    assert row["listed_count"] == 1


def test_internship_never_stretch():
    engine = MatchingEngine()
    job = _job(
        [("sql", True)],
        title="Senior Software Intern",
        is_internship=True,
        experience_level="5+ years",
    )
    assert engine.job_is_stretch(job, junior_cv=True) is False


def test_architect_title_is_stretch_architecture_is_not():
    engine = MatchingEngine()
    architect = _job(
        [("javascript", True)],
        title="Mobile / Web Architect (React / React Native)",
        is_internship=False,
        experience_level=None,
    )
    architecture = _job(
        [("revit", True)],
        title="Architecture Engineer",
        is_internship=False,
        experience_level="Entry-level",
    )
    assert engine.job_is_stretch(architect, True) is True
    assert engine.job_is_stretch(architecture, True) is False


def test_sort_puts_interns_before_stretch():
    engine = MatchingEngine()
    rows = [
        {
            "seniority": "stretch",
            "is_internship": False,
            "experience_level": "5+ years",
            "compatibility_score": 90,
        },
        {
            "seniority": "fit",
            "is_internship": True,
            "experience_level": "Internship",
            "compatibility_score": 40,
        },
    ]
    rows.sort(key=engine._sort_key)
    assert rows[0]["is_internship"] is True
    assert rows[1]["seniority"] == "stretch"


def test_empty_exp_with_internship_mentions_is_junior():
    engine = MatchingEngine()
    assert engine.candidate_is_junior({"internship_mentions": ["summer intern"]}) is True
    assert engine.candidate_is_junior({"experience_level": "5+ years"}) is False
