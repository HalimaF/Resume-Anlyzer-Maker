"""Enhanced Scoring System with Component Breakdown"""

from typing import Dict, List, Any


def calculate_comprehensive_score(
    skill_analysis: Dict[str, Any],
    extracted_text: str,
    jd_score: int | None,
    structure_analysis: Dict[str, Any],
    ats_check: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calculate a comprehensive score with detailed breakdown.
    
    Scoring Model:
    - Keyword Matching (30%): How well skills match job requirements
    - Content Quality (20%): Grammar, completeness, detailed achievements
    - Structure & Format (20%): CV organization, proper sections
    - ATS Compliance (20%): Parsing friendliness, format standards
    - Experience Relevance (10%): Years of experience and career progression
    """
    
    text_length = len(extracted_text.split())
    detected_skills_count = len(skill_analysis.get("detected_skills", []))
    missing_skills_count = len(skill_analysis.get("missing_skills", []))
    
    # 1. Keyword Matching Score (30%)
    total_skills = detected_skills_count + missing_skills_count
    keyword_score = 0
    if total_skills > 0:
        keyword_score = (detected_skills_count / total_skills) * 100
    else:
        keyword_score = 50
    
    if jd_score:
        keyword_score = (keyword_score + jd_score) / 2
    
    # 2. Content Quality Score (20%)
    content_quality = 0
    quality_factors = {
        "has_summary": 1 if any(word in extracted_text.lower() for word in ["summary", "professional", "objective"]) else 0,
        "has_achievements": 1 if any(word in extracted_text.lower() for word in ["achieved", "increased", "improved", "led", "managed"]) else 0,
        "detailed_content": min(text_length / 800, 1) * 100,  # Target 800+ words
        "has_metrics": 1 if any(char.isdigit() for char in extracted_text) else 0,
    }
    
    content_quality = (
        (quality_factors["has_summary"] * 20) +
        (quality_factors["has_achievements"] * 20) +
        (quality_factors["detailed_content"]) +
        (quality_factors["has_metrics"] * 10)
    ) / 50 * 100
    
    # 3. Structure & Format Score (20%)
    structure_score = structure_analysis.get("section_coverage_score", 50)
    
    # 4. ATS Compliance Score (20%)
    ats_score_value = ats_check.get("ats_score", 50)
    
    # 5. Experience Relevance Score (10%) - inferred from mentions of years/roles
    experience_score = 0
    experience_keywords = ["year", "years of experience", "senior", "lead", "manager"]
    if any(keyword.lower() in extracted_text.lower() for keyword in experience_keywords):
        experience_score = 75
    else:
        experience_score = 50
    
    # Calculate weighted total (normalized to 0-100)
    total_score = (
        (keyword_score * 0.30) +
        (content_quality * 0.20) +
        (structure_score * 0.20) +
        (ats_score_value * 0.20) +
        (experience_score * 0.10)
    )
    
    return {
        "overall_score": int(total_score),
        "score_breakdown": {
            "keyword_matching": {
                "score": int(keyword_score),
                "weight": 0.30,
                "description": "Skill alignment with job requirements"
            },
            "content_quality": {
                "score": int(content_quality),
                "weight": 0.20,
                "description": "Quality of descriptions and achievements"
            },
            "structure_format": {
                "score": int(structure_score),
                "weight": 0.20,
                "description": "CV organization and section completeness"
            },
            "ats_compliance": {
                "score": int(ats_score_value),
                "weight": 0.20,
                "description": "Compatibility with automated tracking systems"
            },
            "experience_relevance": {
                "score": int(experience_score),
                "weight": 0.10,
                "description": "Career level and progression indicators"
            }
        },
        "quality_metrics": {
            "text_length": text_length,
            "detected_skills_count": detected_skills_count,
            "missing_skills_count": missing_skills_count,
            "has_achievement_metrics": quality_factors["has_metrics"] == 1,
            "has_professional_summary": quality_factors["has_summary"] == 1,
        }
    }


def compare_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank and compare multiple candidates based on comprehensive scoring.
    
    Args:
        candidates: List of candidate analysis results
        
    Returns:
        Ranked list with percentile rankings
    """
    if not candidates:
        return []
    
    # Sort by score descending
    ranked = sorted(candidates, key=lambda c: c.get("overall_score", 0), reverse=True)
    
    # Add rankings and percentiles
    total = len(ranked)
    for idx, candidate in enumerate(ranked, 1):
        candidate["rank"] = idx
        candidate["percentile"] = int(((total - idx) / total) * 100)
    
    return ranked


def generate_candidate_report(analysis: Dict[str, Any], candidate_name: str = "Candidate") -> Dict[str, Any]:
    """
    Generate a comprehensive report for a single candidate.
    """
    score_breakdown = analysis.get("score_breakdown", {})
    
    # Generate insights
    insights = []
    overall = analysis.get("overall_score", 0)
    
    if overall >= 85:
        insights.append("Excellent fit for the role. Strong match across all categories.")
    elif overall >= 70:
        insights.append("Good fit for the role with some areas for improvement.")
    elif overall >= 55:
        insights.append("Moderate match. Review specific gaps before proceeding.")
    else:
        insights.append("Limited match. Consider looking for other candidates with stronger qualifications.")
    
    # Find weakest areas
    weakest_aspects = sorted(
        score_breakdown.items(),
        key=lambda x: x[1].get("score", 0)
    )[:2]
    
    for aspect_name, aspect_data in weakest_aspects:
        if aspect_data.get("score", 0) < 70:
            insights.append(f"Needs improvement in {aspect_data.get('description', aspect_name)}")
    
    return {
        "candidate_name": candidate_name,
        "overall_score": overall,
        "score_breakdown": score_breakdown,
        "insights": insights,
        "recommendation": "Interview" if overall >= 70 else "Review further" if overall >= 55 else "Not recommended"
    }
