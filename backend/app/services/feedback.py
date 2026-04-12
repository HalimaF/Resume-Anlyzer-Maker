from typing import Dict, List


def _format_skill_examples(skills: List[str], limit: int = 8) -> str:
    return ", ".join(skills[:limit]) if skills else "none"


def generate_feedback(analysis: Dict) -> Dict[str, List[str]]:
    """Create professional natural-language feedback from analysis signals."""
    detected = analysis.get("detected_skills", [])
    missing = analysis.get("missing_skills", [])
    score = analysis.get("resume_score", 0)

    summary = []
    suggestions = []

    if score >= 80:
        summary.append(
            "Your resume demonstrates strong coverage of relevant technical skills and a clear professional structure."
        )
    elif score >= 60:
        summary.append(
            "Your resume has a solid foundation, but targeted improvements can significantly increase your interview readiness."
        )
    else:
        summary.append(
            "Your resume needs stronger alignment with core role expectations and clearer evidence of your technical capabilities."
        )

    summary.append(
        f"Detected strengths include: {_format_skill_examples(detected)}."
    )

    if missing:
        suggestions.append(
            "Add the missing skills only where you have real exposure, then support each one with an achievement-focused bullet."
        )
        suggestions.append(
            f"Prioritize these skills first: {_format_skill_examples(missing)}."
        )
    else:
        suggestions.append(
            "Excellent skill coverage. Focus next on demonstrating measurable impact, ownership, and cross-team collaboration."
        )

    suggestions.extend(
        [
            "Use concise bullet points that follow an action-result format (what you built, how you built it, and what changed).",
            "Quantify outcomes with metrics such as latency reduction, revenue impact, model accuracy, or delivery speed.",
            "Tailor your summary and top projects for each role so your strongest evidence appears in the first screen view.",
        ]
    )

    return {
        "professional_summary": summary,
        "suggestions": suggestions,
    }
