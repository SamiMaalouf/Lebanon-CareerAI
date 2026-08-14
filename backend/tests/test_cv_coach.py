from backend.app.services.cv_coach import CVCoach
from backend.app.services.skill_filters import (
    education_field_to_category,
    is_technical,
    skill_fits_category,
)
from data_pipeline.taxonomy.loader import load_taxonomy


def test_soft_skills_are_not_technical():
    tax = load_taxonomy()
    assert is_technical(tax, "communication") is False
    assert is_technical(tax, "leadership") is False
    assert is_technical(tax, "english") is False
    assert is_technical(tax, "python") is True
    assert is_technical(tax, "git") is True
    assert skill_fits_category(tax, "autocad", "Software Engineering") is False
    assert skill_fits_category(tax, "git", "Software Engineering") is True
    assert skill_fits_category(tax, "python", "Software Engineering") is True
    c = CVCoach()
    assert c._skill_fits_category("autocad", "Software Engineering") is False


def test_mechatronics_robotics_skills_fit_mech_and_elec():
    tax = load_taxonomy()
    assert tax.skills["mechatronics___robotics"]["name"] == "Mechatronics / Robotics"
    assert skill_fits_category(tax, "ros", "Mechatronics Engineering") is True
    assert skill_fits_category(tax, "sensors", "Mechanical Engineering") is True
    assert skill_fits_category(tax, "control_systems", "Robotics") is True
    assert skill_fits_category(tax, "actuators", "Electrical Engineering") is True
    assert skill_fits_category(tax, "ros", "Software Engineering") is False


def test_civil_skills_fit_civil_and_architecture():
    tax = load_taxonomy()
    assert skill_fits_category(tax, "revit", "Civil Engineering") is True
    assert skill_fits_category(tax, "bim", "Architecture") is True
    assert skill_fits_category(tax, "etabs", "Software Engineering") is False


def test_education_field_maps_degrees_to_categories():
    assert education_field_to_category("Computer Science") == "Software Engineering"
    assert education_field_to_category("Computer Engineering") == "Software Engineering"
    assert education_field_to_category("Mechanical Engineering") == "Mechanical Engineering"


def test_cv_fixes_flags_missing_projects_and_major():
    c = CVCoach()
    fixes = {f["id"]: f for f in c._cv_fixes({"skills": ["Python"], "languages": ["Arabic"]})}
    assert fixes["projects"]["ok"] is False
    assert fixes["major"]["ok"] is False
    assert fixes["english"]["ok"] is False
    assert "Forensic" not in fixes["projects"]["action"]
    assert "Computer Engineering" not in fixes["major"]["action"]


def test_cv_fixes_major_uses_selected_category():
    c = CVCoach()
    fixes = {f["id"]: f for f in c._cv_fixes({"skills": ["Python"]}, category="Mechanical Engineering")}
    assert "Mechanical Engineering" in fixes["major"]["action"]


def test_cv_fixes_hides_passing_checks():
    c = CVCoach()
    fixes = c._cv_fixes(
        {
            "projects": ["Campus App 200 users", "Robot Arm"],
            "projects_section_found": True,
            "detected_sections": ["education", "projects", "skills"],
            "education_fields": ["Computer Engineering"],
            "languages": ["English", "Arabic"],
            "skills": ["Python", "Git", "SQL", "JavaScript"],
        }
    )
    assert fixes == []
