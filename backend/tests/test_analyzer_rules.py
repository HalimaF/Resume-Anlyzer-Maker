"""Unit tests for the specific detection rules that used to be wrong."""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.services.analyzer import (  # noqa: E402
    analyze_resume_structure,
    compare_with_job_description,
    detect_skills,
)
from app.services.scoring import infer_years_of_experience, quantified_bullet_ratio  # noqa: E402
from app.services.text_utils import heading_of  # noqa: E402

SKILLS_FILE = BACKEND / "app" / "data" / "skills.json"


def found(text: str, job_description: str = ""):
    return set(detect_skills(text, SKILLS_FILE, job_description)["detected_skills"])


def test_cpp_does_not_also_report_bare_c():
    skills = found("Skills\nC++, Python, Docker")
    assert "C++" in skills
    assert "C" not in skills


def test_csharp_does_not_also_report_bare_c():
    assert "C" not in found("Skills\nC#, ASP.NET, SQL Server")


def test_bare_c_is_found_in_a_real_list():
    assert "C" in found("Skills\nC, Rust, embedded systems programming")


def test_excel_the_verb_is_not_the_spreadsheet():
    assert "Excel" not in found("Profile\nI excel at building teams and shipping software.")


def test_excel_the_product_is_detected():
    assert "Excel" in found("Skills\nMicrosoft Excel, pivot tables, VBA macros")


def test_negated_skill_is_not_counted():
    result = detect_skills("I have no experience with Kubernetes.", SKILLS_FILE)
    assert "Kubernetes" not in result["detected_skills"]
    assert "Kubernetes" in result["disclaimed_skills"]


def test_negation_reaches_across_a_conjunction():
    result = detect_skills("I have no experience with Kubernetes or Terraform yet.", SKILLS_FILE)
    assert "Kubernetes" not in result["detected_skills"]
    assert "Terraform" not in result["detected_skills"]


def test_aspirational_mention_is_not_counted():
    result = detect_skills("I am currently learning Rust and want to learn Go.", SKILLS_FILE)
    assert "Rust" not in result["detected_skills"]
    assert "Go" not in result["detected_skills"]


def test_machine_learning_survives_the_learning_negation_cue():
    assert "Machine Learning" in found("Built machine learning pipelines in production.")


def test_negation_does_not_leak_past_a_sentence_boundary():
    result = detect_skills(
        "I have no experience with Terraform. I use Docker every day.", SKILLS_FILE
    )
    assert "Docker" in result["detected_skills"]
    assert "Terraform" not in result["detected_skills"]


def test_positive_mention_outranks_a_single_disclaimer():
    result = detect_skills(
        "Skills\nDocker, Kubernetes\n\nI had no experience with Docker before 2020.",
        SKILLS_FILE,
    )
    assert "Docker" in result["detected_skills"]
    assert "Docker" not in result["disclaimed_skills"]


def test_aliases_resolve_to_canonical_names():
    skills = found("Skills\nGolang, k8s, Postgres, sklearn, Node JS")
    assert {"Go", "Kubernetes", "PostgreSQL", "Scikit-learn", "Node.js"} <= skills


def test_non_technical_professions_are_covered():
    nurse = found("Skills\nPatient care, triage, medication administration, EHR")
    assert {"Patient Care", "Triage", "Medication Administration"} <= nurse

    marketer = found("Skills\nSEO, content marketing, marketing automation, brand strategy")
    assert {"SEO", "Content Marketing", "Marketing Automation", "Brand Strategy"} <= marketer


def test_email_initial_is_not_a_programming_language():
    assert "R" not in found("Rachel Adeyemi\nr.adeyemi@example.com\nProfile\nSolicitor.")


# --- section detection ------------------------------------------------------

def test_prose_mention_is_not_a_section_heading():
    structure = analyze_resume_structure(
        "About Me\nI wrote the executive summary for an education technology client."
    )
    assert "education" not in structure["present_sections"]


def test_real_heading_is_recognised():
    structure = analyze_resume_structure("EDUCATION\nBSc Computer Science, 2020")
    assert "education" in structure["present_sections"]


def test_heading_with_decoration_is_recognised():
    assert heading_of(">> SCHOOLING") == "education"
    assert heading_of("Technical Skills:") == "skills"
    assert heading_of("--- Work Experience ---") == "experience"


def test_sentence_is_never_a_heading():
    assert heading_of("I studied education policy at university.") == ""


def test_unconventional_skills_heading_falls_back_to_structure():
    structure = analyze_resume_structure("WHAT I KNOW\nReact, TypeScript, CSS, HTML, Git")
    assert "skills" in structure["present_sections"]


# --- scoring helpers --------------------------------------------------------

def test_years_prefers_an_explicit_claim():
    assert infer_years_of_experience("Backend engineer with 6 years of experience.") == 6.0


def test_years_falls_back_to_dated_role_spans():
    years = infer_years_of_experience("Engineer, Acme (2015 - 2021)\nAnalyst, Beta (2012 - 2015)")
    assert years == 9.0


def test_quantified_bullet_ratio_counts_numbers():
    result = quantified_bullet_ratio(
        "- Cut latency by 38%\n- Managed the release process\n- Saved $400k annually"
    )
    assert result["total"] == 3
    assert result["quantified"] == 2
    assert result["unquantified_examples"] == ["Managed the release process"]


# --- job description comparison --------------------------------------------

def test_jd_match_is_driven_by_skills_not_boilerplate():
    resume = "Skills\nPython, Django, PostgreSQL, Docker, AWS"
    jd = (
        "We are a fast-growing company looking for a passionate candidate to join our "
        "world-class team. Competitive salary, generous holiday, and great benefits. "
        "You must have experience with Python, Django, PostgreSQL, Docker and AWS."
    )
    result = compare_with_job_description(resume, jd, SKILLS_FILE)
    assert result["skill_match_score"] == 100
    # Boilerplate drags raw wording overlap down, but must not dominate the score.
    assert result["job_description_match_score"] >= 80


def test_missing_skills_are_named_not_just_counted():
    result = compare_with_job_description(
        "Skills\nPython", "Requires Python, Kubernetes and Terraform.", SKILLS_FILE
    )
    assert set(result["missing_skills"]) == {"Kubernetes", "Terraform"}


# --- metric detection -------------------------------------------------------
# Regression guard: an earlier pattern accepted only percentages, currency and
# 3-or-more-digit counts, so a resume full of real numbers reported "0 of 11
# bullets with numbers" and was told to quantify what was already quantified.

def test_plain_counts_are_metrics():
    from app.services.scoring import has_metric
    assert has_metric("Built 12 microservices in Python")
    assert has_metric("Mentored 4 junior engineers")
    assert has_metric("Cut inference time from 45ms to 6ms")


def test_percentages_and_currency_are_metrics():
    from app.services.scoring import has_metric
    assert has_metric("Reduced p95 latency by 38%")
    assert has_metric("Closed $3.2M in new business")
    assert has_metric("Improved throughput 4x")


def test_a_calendar_year_is_not_a_metric():
    from app.services.scoring import has_metric
    assert not has_metric("Software Engineer, Acme (2021 - 2023)")
    assert not has_metric("Graduated in 2019")


def test_prose_without_numbers_is_not_a_metric():
    from app.services.scoring import has_metric
    assert not has_metric("Responsible for maintaining the deployment pipeline")
    assert not has_metric("Worked closely with the product team")


def test_quantified_ratio_counts_plain_numbers():
    result = quantified_bullet_ratio(
        "- Built 12 microservices\n"
        "- Mentored 4 engineers\n"
        "- Responsible for the deployment pipeline"
    )
    assert result["total"] == 3
    assert result["quantified"] == 2
    assert result["unquantified_examples"] == ["Responsible for the deployment pipeline"]


def test_alternative_bullet_glyphs_are_recognised():
    # PDF extraction rarely yields a plain hyphen.
    for glyph in ("•", "●", "○", "‣", "▸", "–"):
        result = quantified_bullet_ratio(f"{glyph} Shipped 12 features")
        assert result["total"] == 1, f"glyph {glyph!r} was not recognised as a bullet"
        assert result["quantified"] == 1


def test_word_count_is_reported_consistently():
    """The header figure and the length advice must agree.

    They used two different counters, so one resume was shown as both
    "102 words" and "it is only 79 words" on the same screen.
    """
    from app.services.analyzer import run_ats_checker
    from app.services.scoring import calculate_comprehensive_score

    text = (
        "Halima Fahim\nhalima@example.com\n\nSUMMARY\nAI engineer, 4 years.\n\n"
        "EXPERIENCE\nAI Engineer, Vector Labs (2022 - Present)\n"
        "- Built 12 pipelines serving 3 teams\n- Cut latency 38%\n\n"
        "SKILLS\nPython, PyTorch, Docker\n"
    )
    structure = analyze_resume_structure(text)
    ats = run_ats_checker(text, ["Python", "PyTorch", "Docker"], structure)
    comprehensive = calculate_comprehensive_score({}, text, None, structure, ats)

    assert ats["word_count"] == comprehensive["quality_metrics"]["text_length"]
