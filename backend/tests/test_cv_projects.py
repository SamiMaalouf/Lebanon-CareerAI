"""Unit tests for strict Projects-section title extraction."""

from backend.app.services.cv_analyzer import CVAnalyzer, _match_section_header


def test_exact_projects_header():
    a = CVAnalyzer()
    out = a.analyze_text(
        "EDUCATION\nBS Engineering\nPROJECTS\n- Robot Arm Controller\n- IoT Weather Station\nSKILLS\nPython\n"
    )
    assert out["projects_section_found"] is True
    assert "projects" in out["detected_sections"]
    assert out["projects"] == ["Robot Arm Controller", "IoT Weather Station"]


def test_academic_projects_header():
    a = CVAnalyzer()
    out = a.analyze_text(
        "ACADEMIC PROJECTS\nSmart Irrigation System\nLine Follower Robot\nEXPERIENCE\nIntern at ACME\n"
    )
    assert out["projects_section_found"] is True
    assert "Smart Irrigation System" in out["projects"]
    assert "Line Follower Robot" in out["projects"]
    assert "Intern at ACME" not in out["projects"]


def test_glued_projects_pdf_line():
    a = CVAnalyzer()
    out = a.analyze_text(
        "SKILLS\nPython, C++\nPROJECTS Smart Home Automation\nBattery Management System\nEDUCATION\nAUB\n"
    )
    assert out["projects_section_found"] is True
    assert "Smart Home Automation" in out["projects"]
    assert "Battery Management System" in out["projects"]


def test_title_em_dash_description():
    a = CVAnalyzer()
    out = a.analyze_text(
        "Projects\n"
        "Campus Navigation App — built a React Native app for AUB students with offline maps\n"
        "Skills\nReact\n"
    )
    assert out["projects"] == ["Campus Navigation App"]


def test_no_projects_section():
    a = CVAnalyzer()
    out = a.analyze_text("EDUCATION\nBS\nEXPERIENCE\n- Built APIs at work\nSKILLS\nPython\n")
    assert out["projects_section_found"] is False
    assert out["projects"] == []
    assert "projects" not in out["detected_sections"]


def test_match_projects_and_research():
    assert _match_section_header("Projects & Research") == ("projects", "")
    assert _match_section_header("PROJECTS") == ("projects", "")
    assert _match_section_header("PROJECTS Smart Home") == ("projects", "Smart Home")


def test_bullet_prefixed_projects_header():
    from backend.app.services.cv_analyzer import CVAnalyzer

    a = CVAnalyzer()
    out = a.analyze_text("• Projects\n- Campus App\nLanguages\nEnglish\n")
    assert out["projects_section_found"] is True
    assert "Campus App" in out["projects"]


def test_side_by_side_headers():
    from backend.app.services.cv_analyzer import CVAnalyzer, _split_side_by_side_headers

    assert _split_side_by_side_headers("EXPERIENCE PROJECTS") == [
        ("experience", ""),
        ("projects", ""),
    ]
    a = CVAnalyzer()
    out = a.analyze_text("EXPERIENCE PROJECTS\nIntern\nSmart Home\nLANGUAGES\nEnglish\n")
    assert out["projects_section_found"] is True
    assert "experience" in out["detected_sections"]


def test_titles_only_not_description_bullets():
    a = CVAnalyzer()
    text = """
PROJECTS
Forensic Crime Analysis Agent
LangChain.
Implemented semantic hybrid search with evidence
weighting and contradiction detection.
Secured data pipelines using AES-256-CBC
encryption and HMAC-SHA256 integrity checks.
Developed a conversational investigative interface
Programmable Matter Simulation
Implemented A*, BFS, Minimax, Expectimax, and
Hungarian Algorithm for task assignment and
pathfinding.
Designed agent coordination, deadlock handling,
AI Debate Arena
Built a multi-agent debate system
SKILLS
Python
"""
    out = a.analyze_text(text)
    assert out["projects_section_found"] is True
    assert out["projects"] == [
        "Forensic Crime Analysis Agent",
        "Programmable Matter Simulation",
        "AI Debate Arena",
    ]
