from data_pipeline.cleaning.company import (
    clean_company,
    infer_company_from_text,
    is_placeholder_company,
    resolve_company,
)


def test_placeholder_hirelebanese_chrome():
    assert is_placeholder_company("Candidate Sign up") is True
    assert is_placeholder_company("sign up") is True
    assert is_placeholder_company("N/A") is True
    assert is_placeholder_company("Apply now") is True
    assert is_placeholder_company("Confidential 1") is True
    assert is_placeholder_company("Confidentially") is True
    assert is_placeholder_company("Energy Jobline ZR") is True
    assert clean_company("Candidate Sign up") is None


def test_real_company_names_kept():
    assert is_placeholder_company("Murex") is False
    assert is_placeholder_company("EST. Riad Chehab Trading") is False
    assert clean_company("  Bank Audi  ") == "Bank Audi"


def test_infer_company_from_description():
    text = (
        "Company Description\n"
        "NaftPlus IT Department is a technology-driven division focused on ERP.\n"
        "Job Description\nBuild features."
    )
    assert infer_company_from_text(text) == "NaftPlus"
    assert resolve_company("Candidate Sign up", text) == "NaftPlus"
    assert infer_company_from_text("Company Description\nJob Description\nAbout the Role") is None
