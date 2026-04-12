import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional


WORD_PATTERN = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.#-]{1,}\b")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def load_skills(skills_file: Path) -> List[str]:
    """Load predefined skills from JSON dataset."""
    with skills_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("skills", [])


def detect_skills(resume_text: str, skills_list: List[str]) -> Dict[str, List[str]]:
    """Detect present and missing skills using keyword matching."""
    normalized_resume = normalize_text(resume_text)

    detected = []
    for skill in skills_list:
        skill_pattern = re.escape(skill.lower())
        if re.search(rf"(?<!\w){skill_pattern}(?!\w)", normalized_resume):
            detected.append(skill)

    missing = [skill for skill in skills_list if skill not in detected]

    return {
        "detected_skills": sorted(detected, key=str.lower),
        "missing_skills": sorted(missing, key=str.lower),
    }


def keyword_frequency(text: str, top_n: int = 15) -> List[Dict[str, int]]:
    """Return top keywords to provide transparent analysis context."""
    tokens = WORD_PATTERN.findall(normalize_text(text))
    stopwords = {
        "and",
        "the",
        "for",
        "with",
        "from",
        "that",
        "this",
        "your",
        "you",
        "have",
        "are",
        "was",
        "will",
        "using",
        "into",
        "over",
        "than",
        "role",
        "work",
        "experience",
    }
    filtered = [token for token in tokens if token not in stopwords and len(token) > 2]
    top = Counter(filtered).most_common(top_n)
    return [{"keyword": k, "count": v} for k, v in top]


def analyze_resume_structure(resume_text: str) -> Dict:
    """Evaluate resume section completeness for ATS readiness feedback."""
    normalized_resume = normalize_text(resume_text)
    sections = {
        "summary": ["summary", "profile", "objective"],
        "experience": ["experience", "employment", "work history"],
        "education": ["education", "university", "college"],
        "projects": ["projects", "portfolio", "case study"],
        "certifications": ["certification", "certificate", "license"],
        "skills": ["skills", "technical skills", "core skills"],
    }

    section_presence = {}
    for section_name, aliases in sections.items():
        section_presence[section_name] = any(alias in normalized_resume for alias in aliases)

    present_sections = [name for name, is_present in section_presence.items() if is_present]
    missing_sections = [name for name, is_present in section_presence.items() if not is_present]
    coverage_score = round((len(present_sections) / len(sections)) * 100)

    readiness_tips = []
    if missing_sections:
        readiness_tips.append(
            "Add explicit section headings for better ATS parsing: " + ", ".join(missing_sections[:4]) + "."
        )
    if not section_presence["experience"]:
        readiness_tips.append("Include measurable achievements in an Experience section to improve recruiter confidence.")
    if not section_presence["skills"]:
        readiness_tips.append("Add a dedicated Skills section with role-relevant tools and technologies.")
    if not readiness_tips:
        readiness_tips.append("Resume structure is ATS-friendly. Keep section titles clear and consistently formatted.")

    return {
        "section_coverage_score": coverage_score,
        "present_sections": present_sections,
        "missing_sections": missing_sections,
        "ats_readiness_tips": readiness_tips,
    }


def run_ats_checker(resume_text: str, detected_skills: List[str]) -> Dict:
    """Return ATS-focused checks, score, and recommendations."""
    normalized_resume = normalize_text(resume_text)
    word_count = len(WORD_PATTERN.findall(normalized_resume))

    checks = {
        "has_contact_email": bool(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", resume_text)),
        "has_contact_phone": bool(re.search(r"\+?\d[\d\s().-]{7,}\d", resume_text)),
        "has_experience_section": any(term in normalized_resume for term in ["experience", "employment", "work history"]),
        "has_education_section": any(term in normalized_resume for term in ["education", "university", "college"]),
        "has_skills_section": any(term in normalized_resume for term in ["skills", "technical skills", "core skills"]),
        "has_action_verbs": any(term in normalized_resume for term in ["built", "developed", "designed", "implemented", "optimized"]),
        "reasonable_length": 250 <= word_count <= 1200,
        "keyword_density_ok": len(detected_skills) >= 6,
    }

    passed = sum(1 for value in checks.values() if value)
    total = len(checks)
    ats_score = round((passed / total) * 100)

    recommendations = []
    if not checks["has_contact_email"] or not checks["has_contact_phone"]:
        recommendations.append("Add clear contact details (professional email and phone number) at the top.")
    if not checks["has_experience_section"]:
        recommendations.append("Include an Experience section with impact-focused bullet points.")
    if not checks["has_skills_section"]:
        recommendations.append("Add a dedicated Skills section to improve ATS keyword extraction.")
    if not checks["has_action_verbs"]:
        recommendations.append("Start bullets with strong action verbs such as Developed, Built, and Optimized.")
    if not checks["reasonable_length"]:
        recommendations.append("Keep resume length focused (roughly 250-1200 words) for ATS readability.")
    if not checks["keyword_density_ok"]:
        recommendations.append("Increase role-relevant keywords naturally across summary, skills, and projects.")
    if not recommendations:
        recommendations.append("ATS fundamentals look strong. Keep tailoring keywords to each job description.")

    return {
        "ats_score": ats_score,
        "checks": checks,
        "passed_checks": passed,
        "total_checks": total,
        "recommendations": recommendations,
    }


def compare_with_job_description(resume_text: str, job_description: str) -> Dict:
    """Compare resume and job description keywords for targeted suggestions."""
    resume_tokens = set(WORD_PATTERN.findall(normalize_text(resume_text)))
    jd_tokens = WORD_PATTERN.findall(normalize_text(job_description))

    jd_stopwords = {
        "and",
        "the",
        "for",
        "with",
        "you",
        "our",
        "team",
        "role",
        "will",
        "must",
        "years",
        "experience",
        "requirements",
        "responsibilities",
        "skills",
        "ability",
    }
    jd_keywords = [token for token in jd_tokens if token not in jd_stopwords and len(token) > 2]

    unique_jd_keywords = sorted(set(jd_keywords))
    matched = sorted([token for token in unique_jd_keywords if token in resume_tokens])
    missing = sorted([token for token in unique_jd_keywords if token not in resume_tokens])

    match_score = round((len(matched) / max(len(unique_jd_keywords), 1)) * 100)

    improvement_tips = []
    if missing:
        top_missing = missing[:10]
        improvement_tips.append(
            "Consider adding evidence-driven bullets that include these high-value keywords: "
            + ", ".join(top_missing)
            + "."
        )
        improvement_tips.append(
            "Align your project descriptions with the job requirements by naming tools, outcomes, and measurable impact."
        )
    else:
        improvement_tips.append(
            "Great alignment with the job description. Strengthen your profile by adding measurable achievements for each matched keyword."
        )

    return {
        "job_description_match_score": match_score,
        "matched_keywords": matched[:20],
        "missing_jd_keywords": missing[:20],
        "improvement_tips": improvement_tips,
    }


def calculate_resume_score(skill_data: Dict[str, List[str]], resume_text: str, jd_score: Optional[int] = None) -> int:
    """Compute a 0-100 resume score based on skill coverage and structure."""
    detected = len(skill_data.get("detected_skills", []))
    total = detected + len(skill_data.get("missing_skills", []))
    skill_coverage = (detected / total) if total else 0

    normalized_resume = normalize_text(resume_text)
    sections = {
        "summary": ["summary", "profile", "objective"],
        "experience": ["experience", "employment", "work history"],
        "education": ["education", "university", "college"],
        "projects": ["projects", "portfolio", "case study"],
        "certifications": ["certification", "certificate", "license"],
    }
    section_hits = 0
    for aliases in sections.values():
        if any(alias in normalized_resume for alias in aliases):
            section_hits += 1

    structure_score = section_hits / len(sections)

    score = (skill_coverage * 70) + (structure_score * 20)
    if jd_score is not None:
        score += (jd_score / 100) * 10

    return max(0, min(100, round(score)))
