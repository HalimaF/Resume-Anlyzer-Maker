"""Resume analysis: skill detection, structure, ATS checks, and JD comparison."""

import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from .catalog import find_skills, load_categories, load_skills  # noqa: F401  (re-exported)
from .text_utils import (
    DATE_RANGE_PATTERN,
    WORD_PATTERN,
    content_words,
    count_words,
    heading_of,
    normalize_lines,
    normalize_text,
)

SECTION_NAMES = ("summary", "experience", "education", "projects", "certifications", "skills")

ACTION_VERBS = (
    "built", "developed", "designed", "implemented", "optimized", "optimised", "automated",
    "integrated", "collaborated", "assisted", "led", "managed", "delivered", "launched",
    "created", "improved", "reduced", "increased", "coordinated", "analysed", "analyzed",
    "supervised", "trained", "negotiated", "advised", "researched", "produced", "maintained",
)


def detect_skills(
    resume_text: str,
    skills_file: Path,
    job_description: str = "",
) -> Dict[str, object]:
    """Detect resume skills, plus the gap against a target job.

    Without a job description there is no meaningful notion of a "missing"
    skill, so that list stays empty rather than returning the whole catalog.
    """
    resume_result = find_skills(resume_text, skills_file)
    detected = resume_result["detected"]
    detected_set = set(detected)

    required: List[str] = []
    if job_description and job_description.strip():
        required = find_skills(job_description, skills_file)["detected"]

    missing = [skill for skill in required if skill not in detected_set]

    return {
        "detected_skills": detected,
        "disclaimed_skills": resume_result["disclaimed"],
        "missing_skills": missing,
        "required_skills": required,
        "catalog_size": len(load_skills(skills_file)),
    }


def group_by_category(skill_names: List[str], skills_file: Path) -> Dict[str, List[str]]:
    """Group skill names by catalog category, for a scannable UI."""
    categories = load_categories(skills_file)
    grouped: Dict[str, List[str]] = {}
    for name in skill_names:
        grouped.setdefault(categories.get(name, "Other"), []).append(name)
    return {key: sorted(value, key=str.lower) for key, value in sorted(grouped.items())}


def keyword_frequency(text: str, top_n: int = 15) -> List[Dict[str, int]]:
    """Top content keywords, for transparency about what the analyzer saw."""
    top = Counter(content_words(text)).most_common(top_n)
    return [{"keyword": keyword, "count": count} for keyword, count in top]


def analyze_resume_structure(resume_text: str) -> Dict:
    """Evaluate section completeness using real headings, not stray words.

    Detection is heading-anchored: a section counts when a short, unpunctuated
    line names it. Two structural fallbacks catch resumes whose headings are
    unconventional ("WHAT I KNOW") or absent.
    """
    lines = (resume_text or "").splitlines()
    present: Dict[str, bool] = {name: False for name in SECTION_NAMES}

    heading_lines: List[int] = []
    for index, line in enumerate(lines):
        section = heading_of(line)
        if section:
            present[section] = True
            heading_lines.append(index)

    normalized = normalize_lines(resume_text)

    # Fallback 1: a dense comma-separated run of terms is a skills block even
    # when its heading is unconventional.
    if not present["skills"]:
        for line in lines:
            candidate = line.strip()
            if candidate.count(",") >= 3 and len(candidate.split()) <= 30:
                present["skills"] = True
                break

    # Fallback 2: dated role entries evidence work history even when the
    # heading is missing or oddly worded.
    if not present["experience"] and len(DATE_RANGE_PATTERN.findall(resume_text or "")) >= 1:
        if re.search(r"\b(?:at|,)\s+[A-Z][\w&.\- ]{2,}", resume_text or ""):
            present["experience"] = True

    present_sections = [name for name in SECTION_NAMES if present[name]]
    missing_sections = [name for name in SECTION_NAMES if not present[name]]
    coverage_score = round((len(present_sections) / len(SECTION_NAMES)) * 100)

    tips = []
    if missing_sections:
        tips.append(
            "Add explicit section headings so an ATS can parse the document: "
            + ", ".join(missing_sections[:4])
            + "."
        )
    if not present["experience"]:
        tips.append("Add an Experience section with measurable achievements under each role.")
    if not present["skills"]:
        tips.append("Add a dedicated Skills section listing role-relevant tools and methods.")
    if not heading_lines:
        tips.append(
            "No section headings were recognised. Put each heading on its own line, "
            "in a consistent style, with no trailing punctuation."
        )
    if not tips:
        tips.append("Structure is ATS-friendly. Keep heading titles clear and consistently formatted.")

    return {
        "section_coverage_score": coverage_score,
        "present_sections": present_sections,
        "missing_sections": missing_sections,
        "recognised_headings": len(heading_lines),
        "ats_readiness_tips": tips,
    }


def run_ats_checker(resume_text: str, detected_skills: List[str], structure: Optional[Dict] = None) -> Dict:
    """Return ATS-focused checks, a weighted score, and recommendations."""
    text = resume_text or ""
    normalized = normalize_text(text)
    word_count = count_words(text)
    skill_threshold = 3 if word_count < 350 else 5

    structure = structure if structure is not None else analyze_resume_structure(text)
    sections = set(structure.get("present_sections", []))

    checks = {
        "has_contact_email": bool(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)),
        "has_contact_phone": bool(re.search(r"\+?\d[\d\s().-]{7,}\d", text)),
        "has_experience_section": "experience" in sections,
        "has_education_section": "education" in sections,
        "has_skills_section": "skills" in sections,
        "has_action_verbs": any(
            re.search(rf"(?<!\w){verb}(?!\w)", normalized) for verb in ACTION_VERBS
        ),
        "reasonable_length": 140 <= word_count <= 1600,
        "keyword_density_ok": len(detected_skills) >= skill_threshold,
    }

    weights = {
        "has_contact_email": 16,
        "has_contact_phone": 10,
        "has_experience_section": 18,
        "has_education_section": 10,
        "has_skills_section": 16,
        "has_action_verbs": 10,
        "reasonable_length": 10,
        "keyword_density_ok": 10,
    }
    ats_score = sum(weights[key] for key, passed in checks.items() if passed)

    recommendations = []
    if not checks["has_contact_email"] or not checks["has_contact_phone"]:
        recommendations.append("Put a professional email and phone number at the top of page one.")
    if not checks["has_experience_section"]:
        recommendations.append("Add an Experience section with impact-focused bullet points.")
    if not checks["has_skills_section"]:
        recommendations.append("Add a Skills section so the ATS can extract your keywords reliably.")
    if not checks["has_action_verbs"]:
        recommendations.append("Start each bullet with an action verb: Built, Led, Reduced, Delivered.")
    if not checks["reasonable_length"]:
        if word_count < 140:
            recommendations.append(f"At {word_count} words this is too thin. Aim for 400-800 words.")
        else:
            recommendations.append(f"At {word_count} words this is too long. Trim toward 400-800 words.")
    if not checks["keyword_density_ok"]:
        recommendations.append("Name more of the specific tools and methods you actually use.")
    if not recommendations:
        recommendations.append("ATS fundamentals are solid. Keep tailoring keywords to each job.")

    return {
        "ats_score": ats_score,
        "checks": checks,
        "passed_checks": sum(1 for value in checks.values() if value),
        "total_checks": len(checks),
        "word_count": word_count,
        "recommendations": recommendations,
    }


def compare_with_job_description(
    resume_text: str,
    job_description: str,
    skills_file: Optional[Path] = None,
) -> Dict:
    """Compare a resume against a job description.

    The score is driven by the skills the job actually names, because that is
    what a recruiter screens on. Raw wording overlap is reported alongside it
    but deliberately carries less weight -- matching a JD's prose is a writing
    exercise, not evidence of fit.
    """
    resume_tokens = set(content_words(resume_text))
    jd_terms = sorted(set(content_words(job_description)))

    matched_terms = [term for term in jd_terms if term in resume_tokens]
    missing_terms = [term for term in jd_terms if term not in resume_tokens]
    wording_overlap = round((len(matched_terms) / max(len(jd_terms), 1)) * 100)

    skill_score: Optional[int] = None
    matched_skills: List[str] = []
    missing_skills: List[str] = []

    if skills_file is not None:
        required = find_skills(job_description, skills_file)["detected"]
        have = set(find_skills(resume_text, skills_file)["detected"])
        matched_skills = [skill for skill in required if skill in have]
        missing_skills = [skill for skill in required if skill not in have]
        if required:
            skill_score = round((len(matched_skills) / len(required)) * 100)

    if skill_score is None:
        match_score = wording_overlap
    else:
        # Skills carry the decision; wording is a secondary signal.
        match_score = round(skill_score * 0.75 + wording_overlap * 0.25)

    tips = []
    if missing_skills:
        tips.append(
            "This role names skills your resume does not evidence: "
            + ", ".join(missing_skills[:8])
            + ". Add each one you genuinely have, backed by a specific achievement."
        )
    elif skill_score is not None:
        tips.append(
            "You evidence every skill this job names. Compete on depth now: "
            "attach a measurable outcome to each one."
        )
    if missing_terms[:6]:
        tips.append(
            "Vocabulary the posting uses that your resume does not: "
            + ", ".join(missing_terms[:6])
            + ". Mirror the terms that genuinely describe your work."
        )

    return {
        "job_description_match_score": match_score,
        "skill_match_score": skill_score,
        "wording_overlap_score": wording_overlap,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "matched_keywords": matched_terms[:20],
        "missing_jd_keywords": missing_terms[:20],
        "improvement_tips": tips,
    }
