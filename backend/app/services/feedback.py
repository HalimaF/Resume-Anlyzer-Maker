"""Turn analysis signals into ranked, concrete actions.

The old feedback listed generic advice in a fixed order, which left the reader
to work out what mattered. This module instead estimates how many overall
points each fix is worth and sorts by that, so the first thing on screen is the
highest-leverage change available to this specific resume.
"""

from typing import Any, Dict, List

from .scoring import WEIGHTS

# Weight of each ATS check inside the ATS component, mirroring analyzer.py.
_ATS_WEIGHTS = {
    "has_contact_email": 16,
    "has_contact_phone": 10,
    "has_experience_section": 18,
    "has_education_section": 10,
    "has_skills_section": 16,
    "has_action_verbs": 10,
    "reasonable_length": 10,
    "keyword_density_ok": 10,
}

_SECTION_COUNT = 6  # summary, experience, education, projects, certifications, skills

_ATS_FIXES = {
    "has_contact_email": (
        "Add a professional email address",
        "Put it in the header on page one. Applicant tracking systems that "
        "cannot find an email often discard the file outright.",
        "2 minutes",
    ),
    "has_contact_phone": (
        "Add a phone number",
        "Include the country code so international recruiters can dial it.",
        "1 minute",
    ),
    "has_experience_section": (
        "Add an Experience section",
        "Give it a plain heading on its own line, then one entry per role with "
        "dates. Internships, freelance and volunteer work all count.",
        "20 minutes",
    ),
    "has_education_section": (
        "Add an Education section",
        "Qualification, institution, and year. One line each is enough.",
        "5 minutes",
    ),
    "has_skills_section": (
        "Add a Skills section",
        "A plain comma-separated list under a Skills heading is what parsers "
        "read most reliably. Avoid tables, columns, and rating bars.",
        "10 minutes",
    ),
    "has_action_verbs": (
        "Start every bullet with an action verb",
        "Built, Led, Reduced, Delivered, Negotiated. Drop openers like "
        "'Responsible for' and 'Duties included'.",
        "15 minutes",
    ),
}


def _points(component: str, gain_within_component: float) -> float:
    """Convert a gain inside one component into overall score points."""
    return round(gain_within_component * WEIGHTS[component], 1)


def build_priority_actions(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Rank the available fixes by how many overall points each is worth."""
    actions: List[Dict[str, Any]] = []

    ats = analysis.get("ats_check") or {}
    checks = ats.get("checks") or {}
    structure = analysis.get("structure_analysis") or {}
    metrics = analysis.get("quality_metrics") or {}
    missing_skills = analysis.get("missing_skills") or []
    required_skills = analysis.get("required_skills") or []
    detected_skills = analysis.get("detected_skills") or []
    disclaimed = analysis.get("disclaimed_skills") or []

    # --- ATS checklist failures -------------------------------------------
    for key, passed in checks.items():
        if passed or key not in _ATS_FIXES:
            continue
        title, detail, effort = _ATS_FIXES[key]
        impact = _points("ats_compliance", _ATS_WEIGHTS[key])
        # Section fixes also lift the structure component.
        if key in ("has_experience_section", "has_education_section", "has_skills_section"):
            impact += _points("structure_format", 100 / _SECTION_COUNT)
        actions.append({
            "title": title,
            "detail": detail,
            "impact_points": round(impact, 1),
            "effort": effort,
            "category": "ATS",
        })

    # --- length -------------------------------------------------------------
    if not checks.get("reasonable_length", True):
        words = ats.get("word_count", metrics.get("text_length", 0))
        if words < 140:
            title = f"Expand the resume: it is only {words} words"
            detail = ("Aim for 400-800 words. Add one measurable achievement per role "
                      "and a short summary at the top.")
        else:
            title = f"Cut the resume down: it is {words} words"
            detail = ("Aim for 400-800 words. Remove duties everyone in the role shares "
                      "and keep only what you specifically achieved.")
        actions.append({
            "title": title,
            "detail": detail,
            "impact_points": _points("ats_compliance", _ATS_WEIGHTS["reasonable_length"]),
            "effort": "30 minutes",
            "category": "Length",
        })

    # --- missing sections beyond the ATS checklist --------------------------
    for section in structure.get("missing_sections", []):
        if section in ("experience", "education", "skills"):
            continue  # already covered by the ATS fixes above
        labels = {
            "summary": ("Add a 3-line professional summary",
                        "Open with your role, years of experience, and the single "
                        "outcome you are proudest of. This is the only part many "
                        "recruiters read in full.",
                        "15 minutes"),
            "projects": ("Add a Projects section",
                         "Two or three projects with what you built, the tools you "
                         "used, and the result. This is how you evidence skills you "
                         "have not yet been paid for.",
                         "30 minutes"),
            "certifications": ("Add a Certifications or Awards section",
                               "List credentials, licences, and courses with the issuing "
                               "body and year. Even in-progress ones count if labelled.",
                               "10 minutes"),
        }
        if section in labels:
            title, detail, effort = labels[section]
            impact = _points("structure_format", 100 / _SECTION_COUNT)
            if section == "summary":
                impact += _points("content_quality", 15)
            actions.append({
                "title": title,
                "detail": detail,
                "impact_points": round(impact, 1),
                "effort": effort,
                "category": "Structure",
            })

    # --- quantified outcomes ------------------------------------------------
    bullet_total = metrics.get("bullet_count", 0)
    quantified = metrics.get("quantified_bullets", 0)
    if bullet_total and quantified < bullet_total:
        shortfall = bullet_total - quantified
        examples = metrics.get("unquantified_examples") or []
        detail = (
            f"{shortfall} of your {bullet_total} bullet points state no number. "
            "Attach a percentage, amount, count, or time saved to each one."
        )
        if examples:
            snippet = examples[0][:90] + ("..." if len(examples[0]) > 90 else "")
            detail += f' For example, rewrite: "{snippet}"'
        gain = (1 - (quantified / bullet_total)) * 20
        actions.append({
            "title": f"Quantify {shortfall} more bullet point{'s' if shortfall != 1 else ''}",
            "detail": detail,
            "impact_points": _points("content_quality", gain),
            "effort": f"{max(5, shortfall * 5)} minutes",
            "category": "Impact",
        })
    elif not metrics.get("has_achievement_metrics"):
        actions.append({
            "title": "Add measurable outcomes",
            "detail": ("No numbers were found anywhere in the resume. Percentages, "
                       "revenue, headcount, volume, and time saved are what separate "
                       "a claim from evidence."),
            "impact_points": _points("content_quality", 35),
            "effort": "30 minutes",
            "category": "Impact",
        })

    # --- skill gaps against the target job ----------------------------------
    if missing_skills:
        covered = len(required_skills) - len(missing_skills)
        gain = ((len(required_skills) - covered) / max(len(required_skills), 1)) * 100
        shown = ", ".join(missing_skills[:6])
        actions.append({
            "title": f"Close {len(missing_skills)} skill gap{'s' if len(missing_skills) != 1 else ''} for this role",
            "detail": (f"This job asks for {shown}"
                       f"{' and more' if len(missing_skills) > 6 else ''}, and your resume "
                       "does not evidence them. Add only the ones you genuinely have, "
                       "each backed by a specific achievement."),
            "impact_points": _points("keyword_matching", gain / 2),
            "effort": "20 minutes",
            "category": "Job fit",
        })
    elif len(detected_skills) < 10:
        actions.append({
            "title": "Name more of the tools and methods you use",
            "detail": (f"Only {len(detected_skills)} recognised skill"
                       f"{'s were' if len(detected_skills) != 1 else ' was'} found. "
                       "Be specific: name the software, frameworks, standards, and "
                       "methods rather than describing them generically."),
            "impact_points": _points("keyword_matching", (1 - len(detected_skills) / 10) * 100 / 2),
            "effort": "15 minutes",
            "category": "Job fit",
        })

    # --- disclaimed skills are worth surfacing, but are not a scored fix -----
    if disclaimed:
        actions.append({
            "title": "Review skills you explicitly disclaimed",
            "detail": ("You mention " + ", ".join(disclaimed[:5]) + " in a negative or "
                       "aspirational phrase ('no experience with', 'currently learning'). "
                       "These were not counted. If you do have the skill, state it plainly; "
                       "if not, consider cutting the sentence."),
            "impact_points": 0.0,
            "effort": "5 minutes",
            "category": "Wording",
        })

    actions.sort(key=lambda item: item["impact_points"], reverse=True)
    for rank, action in enumerate(actions, 1):
        action["rank"] = rank
    return actions


def build_strengths(analysis: Dict[str, Any]) -> List[str]:
    """What the resume already does well, stated specifically."""
    strengths: List[str] = []
    metrics = analysis.get("quality_metrics") or {}
    detected = analysis.get("detected_skills") or []
    required = analysis.get("required_skills") or []
    missing = analysis.get("missing_skills") or []
    structure = analysis.get("structure_analysis") or {}
    ats = analysis.get("ats_check") or {}

    if len(detected) >= 10:
        strengths.append(f"{len(detected)} recognised skills, a broad and specific toolkit.")
    if required and not missing:
        strengths.append(f"Evidences all {len(required)} skills this job description names.")
    elif required and len(missing) < len(required) / 2:
        strengths.append(f"Covers {len(required) - len(missing)} of {len(required)} skills this role asks for.")

    total, quantified = metrics.get("bullet_count", 0), metrics.get("quantified_bullets", 0)
    if total and quantified / total >= 0.6:
        strengths.append(f"{quantified} of {total} bullet points carry a hard number.")

    if len(structure.get("missing_sections", [])) == 0:
        strengths.append("Every standard resume section is present and clearly headed.")

    if ats.get("passed_checks") == ats.get("total_checks") and ats.get("total_checks"):
        strengths.append("Passes every ATS parsing check.")

    years = metrics.get("years_of_experience")
    if years and years >= 5:
        strengths.append(f"Around {int(years)} years of experience is clearly evidenced.")

    return strengths


def generate_feedback(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Create the full feedback payload: verdict, strengths, ranked actions."""
    score = analysis.get("resume_score", 0)
    detected = analysis.get("detected_skills") or []
    required = analysis.get("required_skills") or []
    missing = analysis.get("missing_skills") or []
    has_jd = bool((analysis.get("meta") or {}).get("has_job_description"))

    if score >= 85:
        verdict = ("This resume is ready to send. It is well structured, specific, "
                   "and evidences its claims.")
    elif score >= 70:
        verdict = ("A solid resume that a few targeted fixes would make competitive. "
                   "Start with the highest-impact action below.")
    elif score >= 55:
        verdict = ("The foundations are here, but the resume is not yet making its case. "
                   "The actions below are ordered by how much each is worth.")
    else:
        verdict = ("This resume will struggle to get past an initial screen. Work through "
                   "the actions below in order; the first few are worth the most.")

    summary = [verdict]
    if not detected:
        summary.append(
            "No recognised skills were found. Add a clearly headed Skills section "
            "naming the specific tools, systems, and methods you use."
        )
    if has_jd and required:
        summary.append(
            f"Against this job description you evidence {len(required) - len(missing)} "
            f"of the {len(required)} skills it names."
        )
    elif not has_jd:
        summary.append(
            "Paste a target job description to see which of its requirements "
            "your resume does not yet evidence."
        )

    actions = build_priority_actions(analysis)

    return {
        "verdict": verdict,
        "professional_summary": summary,
        "strengths": build_strengths(analysis),
        "priority_actions": actions,
        # Kept for the PDF report and any older client.
        "suggestions": [f"{a['title']}. {a['detail']}" for a in actions],
    }
