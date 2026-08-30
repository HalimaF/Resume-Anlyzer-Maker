"""Parsing a LinkedIn export or a resume into CV Maker fields."""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.services.profile_import import looks_like_linkedin, parse_profile  # noqa: E402

# A LinkedIn "Save to PDF" export as PyMuPDF extracts it: sidebar first, then
# the main column. A teacher, deliberately: nothing here is a tech resume.
LINKEDIN = """Contact
www.linkedin.com/in/sarahokafor
(LinkedIn)
sarah.okafor@example.com
+44 7700 900456

Top Skills
Curriculum Development
Classroom Management
Student Assessment

Certifications
PGCE Secondary Mathematics
Safeguarding Level 3

Sarah Okafor
Head of Mathematics at Brookfield Academy
Manchester, England, United Kingdom

Summary
Secondary mathematics teacher with 9 years in the classroom.

Experience

Brookfield Academy
Head of Mathematics
September 2020 - Present (5 years 11 months)
Manchester, United Kingdom
Lead a department of 7 teachers across 600 students.
Redesigned the KS4 curriculum, lifting pass rates 23 points.

Aldergate School
Mathematics Teacher
September 2016 - August 2020 (4 years)
Leeds, United Kingdom
Taught KS3 and KS4 mathematics to 180 students per year.

Education

University of Manchester
PGCE, Secondary Mathematics Education · (2015 - 2016)

University of Leeds
BSc, Mathematics · (2012 - 2015)

Page 1 of 2
"""

RESUME = """GRACE MENSAH
grace.mensah@example.com | +233 24 123 4567 | Accra, Ghana

SUMMARY
Chartered accountant with 9 years in audit and financial reporting.

EXPERIENCE
Audit Manager, Ledger and Co
2017 - Present
Led statutory audits for 18 clients with combined revenue over $400M.
Reduced the close cycle from 12 days to 7.

Senior Auditor, Meridian LLP
2014 - 2017
Managed a portfolio of 25 mid-market clients.

EDUCATION
University of Ghana
BSc Accounting, 2014

SKILLS
Financial Reporting, Audit, IFRS, Advanced Excel, Time Management, Leadership
"""


def test_linkedin_export_is_recognised():
    assert looks_like_linkedin(LINKEDIN)
    assert not looks_like_linkedin(RESUME)
    assert parse_profile(LINKEDIN)["source"] == "linkedin"
    assert parse_profile(RESUME)["source"] == "resume"


def test_sidebar_skill_is_not_mistaken_for_the_name():
    """"Curriculum Development" is two capitalised words, exactly like a name.

    The profile URL slug disambiguates it.
    """
    profile = parse_profile(LINKEDIN)["profile"]
    assert profile["fullName"] == "Sarah Okafor"


def test_identity_block_is_not_absorbed_by_the_sidebar():
    """The name follows a Certifications heading with no heading in between."""
    profile = parse_profile(LINKEDIN)["profile"]
    assert profile["certifications"] == ["PGCE Secondary Mathematics", "Safeguarding Level 3"]
    assert "Sarah Okafor" not in profile["certifications"]
    assert profile["title"] == "Head of Mathematics at Brookfield Academy"
    assert profile["location"] == "Manchester, England, United Kingdom"


def test_linkedin_contact_details():
    profile = parse_profile(LINKEDIN)["profile"]
    assert profile["email"] == "sarah.okafor@example.com"
    assert profile["phone"] == "+44 7700 900456"
    assert "linkedin.com/in/sarahokafor" in profile["linkedin"]


def test_linkedin_experience_splits_company_and_role():
    experience = parse_profile(LINKEDIN)["profile"]["experience"]
    assert len(experience) == 2
    assert experience[0]["title"] == "Head of Mathematics"
    assert experience[0]["company"] == "Brookfield Academy"
    assert experience[0]["end"] == "Present"
    assert "600 students" in experience[0]["description"]

    assert experience[1]["title"] == "Mathematics Teacher"
    assert experience[1]["company"] == "Aldergate School"


def test_duration_and_page_furniture_are_stripped():
    experience = parse_profile(LINKEDIN)["profile"]["experience"]
    joined = " ".join(entry["description"] for entry in experience)
    assert "5 years 11 months" not in joined
    assert "Page 1 of 2" not in joined


def test_linkedin_education():
    education = parse_profile(LINKEDIN)["profile"]["education"]
    assert len(education) == 2
    assert education[0]["degree"] == "PGCE"
    assert education[0]["school"] == "University of Manchester"
    assert education[1]["degree"] == "BSc"


def test_plain_resume_splits_title_and_employer_on_one_line():
    """"Audit Manager, Ledger and Co" has to become two fields."""
    experience = parse_profile(RESUME)["profile"]["experience"]
    assert len(experience) == 2
    assert experience[0]["title"] == "Audit Manager"
    assert experience[0]["company"] == "Ledger and Co"
    assert experience[1]["title"] == "Senior Auditor"
    assert experience[1]["company"] == "Meridian LLP"


def test_description_sentence_is_not_taken_as_the_next_job_title():
    """The line before a date range is only a header if it reads like one."""
    experience = parse_profile(RESUME)["profile"]["experience"]
    titles = [entry["title"] for entry in experience]
    assert not any(title.endswith(".") for title in titles)
    assert "Reduced the close cycle from 12 days to 7." not in titles


def test_resume_skills_are_comma_split():
    skills = parse_profile(RESUME)["profile"]["skills"]
    assert "Financial Reporting" in skills
    assert "IFRS" in skills
    assert "Leadership" in skills


def test_empty_input_is_reported_not_crashed():
    result = parse_profile("")
    assert result["fields_found"] == 0
    assert result["warnings"]


def test_missing_pieces_are_named_in_warnings():
    result = parse_profile("Just a sentence with no structure at all.")
    joined = " ".join(result["warnings"]).lower()
    assert "experience" in joined
    assert "education" in joined
