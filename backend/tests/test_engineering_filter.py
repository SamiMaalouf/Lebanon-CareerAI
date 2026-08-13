from data_pipeline.cleaning.engineering_filter import (
    annotate_engineering,
    classify_engineering_category,
    is_engineering_role,
)


def test_embedded_and_ce_titles_map_to_software():
    assert classify_engineering_category("Embedded Software Engineer")[0] == "Software Engineering"
    assert classify_engineering_category("Firmware Engineer")[0] == "Software Engineering"
    assert classify_engineering_category("FPGA Design Engineer")[0] == "Software Engineering"
    assert classify_engineering_category("Computer Engineering Intern")[0] == "Software Engineering"


def test_software_engineering_stays_software():
    assert classify_engineering_category("Software Engineer")[0] == "Software Engineering"
    assert classify_engineering_category("Python Developer")[0] == "Software Engineering"
    intern = annotate_engineering(
        {
            "job_title": "Software Engineering Intern",
            "description": "Python internship for CS students.",
        }
    )
    assert intern is not None
    assert intern["job_category"] == "Software Engineering"
    assert intern["is_internship"] is True


def test_non_stem_internships_are_dropped():
    ok, reason = is_engineering_role(
        "Customer Success Intern",
        "We use software tools to support customers.",
    )
    assert ok is False
    assert reason in {"deny_title", "non_eng_internship"}

    ok, reason = is_engineering_role(
        "Accountant Intern",
        "Join our finance team. Excel and software experience a plus.",
    )
    assert ok is False

    ok, reason = is_engineering_role(
        "Summer Intern",
        "Great software company looking for a marketing intern.",
    )
    assert ok is False
    assert reason == "non_eng_internship"


def test_specific_ce_degree_maps_to_software():
    cat, _ = classify_engineering_category(
        "IT Engineer",
        "Bachelor's degree in Computer Engineering required.",
    )
    assert cat == "Software Engineering"


def test_degree_line_does_not_make_software_into_ce():
    cat, _ = classify_engineering_category(
        "Python Developer",
        "Bachelor's degree in Computer Science, Computer Engineering, or related field.",
    )
    assert cat == "Software Engineering"


def test_graduate_ad_leading_with_ce_cce():
    cat, _ = classify_engineering_category(
        "Fresh Engineering & IT Graduates - Dual Nationality",
        "We are looking to hire fresh engineering (CE, CCE, EE, CS, SE) and IT graduates.",
    )
    assert cat == "Software Engineering"


def test_early_stage_is_not_an_internship():
    rec = annotate_engineering(
        {
            "job_title": "Full-Stack Engineer",
            "description": "Move fast in an early-stage environment. React and APIs.",
        }
    )
    assert rec is not None
    assert rec["is_internship"] is False


def test_annotate_overwrites_stale_software_label():
    rec = annotate_engineering(
        {
            "job_title": "Embedded Systems Engineer",
            "description": "Firmware and C on STM32.",
            "job_category": "Software Engineering",
        }
    )
    assert rec is not None
    assert rec["job_category"] == "Software Engineering"
