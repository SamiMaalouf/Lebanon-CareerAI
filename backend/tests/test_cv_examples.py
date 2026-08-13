from backend.app.services.skill_gap import cv_example_for


def test_git_example_mentions_github_under_projects():
    assert cv_example_for("git", "Git") == "Git — GitHub link under Projects"


def test_unknown_skill_gets_generic_fallback():
    line = cv_example_for("obscure_tool", "Obscure Tool")
    assert line.startswith("Obscure Tool —")
    assert "Skills" in line
