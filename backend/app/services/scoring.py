"""Comprehensive scoring model shared by single and bulk resume analysis."""

import re
from typing import Any, Dict, List, Optional

from .text_utils import DATE_RANGE_PATTERN, count_words

# Component weights. These must sum to 1.0.
WEIGHTS = {
    "keyword_matching": 0.30,
    "content_quality": 0.20,
    "structure_format": 0.20,
    "ats_compliance": 0.20,
    "experience_relevance": 0.10,
}

ACHIEVEMENT_VERBS = (
    "achieved", "increased", "improved", "reduced", "led", "managed",
    "delivered", "launched", "scaled", "optimized", "optimised", "automated",
    "grew", "cut", "saved", "exceeded", "won", "shipped",
)

SENIORITY_TERMS = ("senior", "lead", "principal", "staff", "manager", "head of", "director", "chief")

# Unambiguous impact markers: percentages, currency, multipliers, magnitudes.
STRONG_METRIC_PATTERN = re.compile(
    r"\d+\s*%|[$€£¥]\s*\d|\b\d+(?:\.\d+)?\s*[kmb]\b|\b\d+x\b", re.IGNORECASE
)
# Any standalone number. "Built 12 microservices" and "mentored 4 engineers"
# are quantified achievements; an earlier version accepted only percentages,
# currency and 3-or-more-digit counts, so it reported those bullets as having
# no number and told people to quantify what was already quantified.
NUMBER_PATTERN = re.compile(r"(?<![\w.])\d+(?:\.\d+)?")
# A calendar year is a date, not a measurement.
YEAR_PATTERN = re.compile(r"^(?:19|20)\d{2}$")

YEARS_PATTERN = re.compile(r"(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b", re.IGNORECASE)
# Bullet lines, used to judge how much of the writing is evidence-backed.
# PDF extraction emits a wide range of glyphs, so accept the common ones.
BULLET_PATTERN = re.compile(r"^\s*[-*•·▪●○◦‣⁃▸▹»–—]\s+(.+)$", re.MULTILINE)


def has_metric(text: str) -> bool:
    """Whether a piece of writing states a measurable outcome."""
    text = text or ""
    if STRONG_METRIC_PATTERN.search(text):
        return True
    return any(
        not YEAR_PATTERN.match(match.group(0))
        for match in NUMBER_PATTERN.finditer(text)
    )


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Constrain a score so no component can skew the weighted total."""
    return max(low, min(high, value))


def quantified_bullet_ratio(text: str) -> Dict[str, Any]:
    """How many bullet points carry a number.

    This is the single most actionable content signal: recruiters skim for
    outcomes, and a bullet without a number rarely states one.
    """
    bullets = [b.strip() for b in BULLET_PATTERN.findall(text or "") if b.strip()]
    if not bullets:
        return {"total": 0, "quantified": 0, "ratio": 0.0, "unquantified_examples": []}

    quantified = [b for b in bullets if has_metric(b)]
    unquantified = [b for b in bullets if not has_metric(b)]
    return {
        "total": len(bullets),
        "quantified": len(quantified),
        "ratio": len(quantified) / len(bullets),
        "unquantified_examples": unquantified[:3],
    }


def _score_content_quality(text: str, word_count: int, structure: Dict[str, Any]) -> Dict[str, Any]:
    """Rate the substance of the writing on a true 0-100 scale."""
    lowered = (text or "").lower()
    sections = set(structure.get("present_sections", []))

    # Trust the heading-anchored structure pass rather than re-guessing from
    # loose substrings, which is what used to count "executive summary" in a
    # sentence as having a Summary section.
    has_summary = "summary" in sections
    has_achievements = any(
        re.search(rf"(?<!\w){verb}(?!\w)", lowered) for verb in ACHIEVEMENT_VERBS
    )
    bullets = quantified_bullet_ratio(text)
    has_metrics = has_metric(text or "")

    # A focused one-page resume (~500 words) counts as fully detailed.
    depth = min(word_count / 500, 1.0)

    score = (
        (15 if has_summary else 0)
        + (20 if has_achievements else 0)
        + (depth * 30)
        + (15 if has_metrics else 0)
        # Reward the share of bullets that actually quantify an outcome.
        + (bullets["ratio"] * 20)
    )

    return {
        "score": _clamp(score),
        "has_summary": has_summary,
        "has_achievements": has_achievements,
        "has_metrics": has_metrics,
        "bullets": bullets,
    }


def infer_years_of_experience(text: str) -> Optional[float]:
    """Best estimate of career length, in years.

    Prefers an explicit claim ("6 years"). Falls back to the span covered by
    dated role entries, which is much harder to inflate accidentally than the
    old behaviour of taking the largest number followed by "years" anywhere in
    the document.
    """
    text = text or ""

    claims = [int(m) for m in YEARS_PATTERN.findall(text) if 0 < int(m) <= 50]
    if claims:
        # The largest *claim* is intentional; a resume saying "8 years" means it.
        return float(max(claims))

    years: List[int] = []
    for match in DATE_RANGE_PATTERN.finditer(text):
        found = re.findall(r"(?:19|20)\d{2}", match.group(0))
        years.extend(int(y) for y in found)
        if re.search(r"present|current|now|date", match.group(0), re.IGNORECASE):
            years.append(2026)

    if len(years) >= 2:
        span = max(years) - min(years)
        if 0 < span <= 50:
            return float(span)
    return None


def _score_experience(text: str) -> float:
    """Infer career level from tenure and seniority signals."""
    years = infer_years_of_experience(text)
    if years is not None:
        return _clamp(55 + min(years, 10) * 4.5)
    if any(term in (text or "").lower() for term in SENIORITY_TERMS):
        return 70.0
    return 45.0


def _score_keywords(
    detected_count: int,
    required: List[str],
    missing: List[str],
    jd_score: Optional[int],
) -> float:
    """Blend raw skill breadth with coverage of the target job."""
    # Most strong resumes surface roughly ten clearly relevant skills.
    components = [min(detected_count / 10, 1.0) * 100]

    if required:
        covered = len(required) - len(missing)
        components.append((covered / len(required)) * 100)

    if jd_score is not None:
        components.append(_clamp(float(jd_score)))

    return _clamp(sum(components) / len(components))


def calculate_comprehensive_score(
    skill_analysis: Dict[str, Any],
    extracted_text: str,
    jd_score: Optional[int],
    structure_analysis: Dict[str, Any],
    ats_check: Dict[str, Any],
) -> Dict[str, Any]:
    """Calculate an overall 0-100 score with a per-component breakdown.

    Every component is independently clamped to 0-100 before weighting, so the
    weighted total is guaranteed to land in 0-100 as well.
    """
    text = extracted_text or ""
    word_count = count_words(text)

    detected = skill_analysis.get("detected_skills") or []
    missing = skill_analysis.get("missing_skills") or []
    required = skill_analysis.get("required_skills") or []

    keyword_score = _score_keywords(len(detected), list(required), list(missing), jd_score)
    content = _score_content_quality(text, word_count, structure_analysis)
    structure_score = _clamp(float(structure_analysis.get("section_coverage_score", 0)))
    ats_score_value = _clamp(float(ats_check.get("ats_score", 0)))
    experience_score = _score_experience(text)

    total_score = _clamp(
        keyword_score * WEIGHTS["keyword_matching"]
        + content["score"] * WEIGHTS["content_quality"]
        + structure_score * WEIGHTS["structure_format"]
        + ats_score_value * WEIGHTS["ats_compliance"]
        + experience_score * WEIGHTS["experience_relevance"]
    )

    return {
        "overall_score": int(round(total_score)),
        "score_breakdown": {
            "keyword_matching": {
                "score": int(round(keyword_score)),
                "weight": WEIGHTS["keyword_matching"],
                "description": "Skill alignment with job requirements",
            },
            "content_quality": {
                "score": int(round(content["score"])),
                "weight": WEIGHTS["content_quality"],
                "description": "Quality of descriptions and achievements",
            },
            "structure_format": {
                "score": int(round(structure_score)),
                "weight": WEIGHTS["structure_format"],
                "description": "CV organization and section completeness",
            },
            "ats_compliance": {
                "score": int(round(ats_score_value)),
                "weight": WEIGHTS["ats_compliance"],
                "description": "Compatibility with automated tracking systems",
            },
            "experience_relevance": {
                "score": int(round(experience_score)),
                "weight": WEIGHTS["experience_relevance"],
                "description": "Career level and progression indicators",
            },
        },
        "quality_metrics": {
            "text_length": word_count,
            "detected_skills_count": len(detected),
            "missing_skills_count": len(missing),
            "required_skills_count": len(required),
            "has_achievement_metrics": content["has_metrics"],
            "has_professional_summary": content["has_summary"],
            "years_of_experience": infer_years_of_experience(text),
            "bullet_count": content["bullets"]["total"],
            "quantified_bullets": content["bullets"]["quantified"],
            "unquantified_examples": content["bullets"]["unquantified_examples"],
        },
    }


def compare_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rank candidates by overall score, attaching rank and percentile.

    Percentile is the share of the field a candidate placed ahead of, so the
    strongest scores 100 and the weakest 0. A lone candidate has no field to
    compare against and is reported at 100.
    """
    if not candidates:
        return []

    ranked = sorted(
        (dict(candidate) for candidate in candidates),
        key=lambda c: c.get("overall_score", 0),
        reverse=True,
    )

    total = len(ranked)
    for idx, candidate in enumerate(ranked, 1):
        candidate["rank"] = idx
        candidate["percentile"] = 100 if total == 1 else int(round(((total - idx) / (total - 1)) * 100))

    return ranked


def generate_candidate_report(analysis: Dict[str, Any], candidate_name: str = "Candidate") -> Dict[str, Any]:
    """Generate a comprehensive report for a single candidate."""
    score_breakdown = analysis.get("score_breakdown") or {}
    overall = analysis.get("overall_score", 0)

    insights = []
    if overall >= 85:
        insights.append("Excellent fit for the role. Strong match across all categories.")
    elif overall >= 70:
        insights.append("Good fit for the role with some areas for improvement.")
    elif overall >= 55:
        insights.append("Moderate match. Review specific gaps before proceeding.")
    else:
        insights.append("Limited match against the stated requirements.")

    scored_aspects = [(name, data) for name, data in score_breakdown.items() if isinstance(data, dict)]
    for aspect_name, aspect_data in sorted(scored_aspects, key=lambda item: item[1].get("score", 0))[:2]:
        if aspect_data.get("score", 0) < 70:
            insights.append(f"Needs improvement in {aspect_data.get('description', aspect_name)}")

    return {
        "candidate_name": candidate_name,
        "overall_score": overall,
        "score_breakdown": score_breakdown,
        "insights": insights,
        "recommendation": "Interview" if overall >= 70 else "Review further" if overall >= 55 else "Not recommended",
    }
