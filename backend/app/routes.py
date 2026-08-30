import re
from io import BytesIO
from pathlib import Path
from tempfile import gettempdir
from typing import Optional, Tuple
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.datastructures import FileStorage

from .services import llm
from .services.analyzer import (
    analyze_resume_structure,
    compare_with_job_description,
    detect_skills,
    group_by_category,
    keyword_frequency,
    load_skills,
    run_ats_checker,
)
from .services.extractor import extract_resume_text
from .services.feedback import generate_feedback
from .services.profile_import import parse_profile
from .services.report_generator import build_report_pdf
from .services.scoring import calculate_comprehensive_score, compare_candidates, generate_candidate_report

api_bp = Blueprint("api", __name__)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


def _save_upload(file: FileStorage) -> Path:
    """Persist an upload under a generated name.

    The extension is taken from the client filename but the stem never is, so
    a hostile name cannot influence the path that gets written.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix.lstrip(".") not in current_app.config["ALLOWED_EXTENSIONS"]:
        suffix = ".bin"

    temp_dir = Path(gettempdir()) / "resume_analyzer_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid4().hex}{suffix}"
    file.save(temp_path)
    return temp_path


def _discard(path: Optional[Path]) -> None:
    """Best-effort cleanup so a failed delete never breaks a response."""
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        current_app.logger.warning("Could not remove temporary upload %s", path)


def _check_file_size(file: FileStorage) -> Optional[str]:
    """Reject an oversized file before it is read, returning an error message."""
    max_bytes = current_app.config["MAX_FILE_SIZE"]
    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > max_bytes:
        return f"{file.filename} is {size / 1048576:.1f} MB. The limit is {max_bytes / 1048576:.0f} MB per file."
    if size == 0:
        return f"{file.filename} is empty."
    return None


def build_analysis_payload(resume_text: str, job_description: str, use_llm: bool = True):
    """Assemble the full analysis response for one resume.

    Shared by the upload and raw-text endpoints so both always report the same
    numbers and the same shape for the same resume.
    """
    skills_file = current_app.config["SKILLS_FILE"]
    skill_analysis = detect_skills(resume_text, skills_file, job_description)

    jd_data = None
    jd_score = None
    if job_description:
        jd_data = compare_with_job_description(resume_text, job_description, skills_file)
        jd_score = jd_data["job_description_match_score"]

    structure_analysis = analyze_resume_structure(resume_text)
    ats_result = run_ats_checker(resume_text, skill_analysis["detected_skills"], structure_analysis)
    comprehensive = calculate_comprehensive_score(
        skill_analysis, resume_text, jd_score, structure_analysis, ats_result
    )

    payload = {
        "resume_score": comprehensive["overall_score"],
        "score_breakdown": comprehensive["score_breakdown"],
        "quality_metrics": comprehensive["quality_metrics"],
        "detected_skills": skill_analysis["detected_skills"],
        "detected_skills_by_category": group_by_category(skill_analysis["detected_skills"], skills_file),
        "disclaimed_skills": skill_analysis["disclaimed_skills"],
        "missing_skills": skill_analysis["missing_skills"],
        "required_skills": skill_analysis["required_skills"],
        "top_keywords": keyword_frequency(resume_text),
        "structure_analysis": structure_analysis,
        "ats_check": ats_result,
        "job_description_analysis": jd_data,
        "meta": {
            "detected_skill_count": len(skill_analysis["detected_skills"]),
            "missing_skill_count": len(skill_analysis["missing_skills"]),
            "required_skill_count": len(skill_analysis["required_skills"]),
            "has_job_description": bool(job_description),
            "catalog_size": skill_analysis["catalog_size"],
        },
    }
    payload["feedback"] = generate_feedback(payload)

    # Enrichment is additive and best-effort: a missing or failing model must
    # never change the score or break the response.
    payload["ai_insights"] = None
    if use_llm:
        payload["ai_insights"] = llm.enrich_analysis(
            current_app.config, resume_text, job_description, skill_analysis["detected_skills"]
        )

    return payload


def _read_upload(file: FileStorage) -> Tuple[Optional[str], Optional[str]]:
    """Extract text from one upload. Returns (text, error_message)."""
    size_error = _check_file_size(file)
    if size_error:
        return None, size_error

    temp_path = None
    try:
        temp_path = _save_upload(file)
        text = extract_resume_text(temp_path)
    except Exception as exc:
        return None, f"Could not read {file.filename}: {exc}"
    finally:
        _discard(temp_path)

    if not text or not text.strip():
        return None, (
            f"No readable text found in {file.filename}. If it is a scanned image, "
            "try exporting a text-based PDF or pasting the text directly."
        )
    return text, None


@api_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "smart-resume-analyzer",
        "skills_in_catalog": len(load_skills(current_app.config["SKILLS_FILE"])),
        "ai_enrichment": llm.status(current_app.config),
        "limits": {
            "max_file_bytes": current_app.config["MAX_FILE_SIZE"],
            "max_bulk_files": current_app.config["MAX_BULK_FILES"],
            "allowed_extensions": sorted(current_app.config["ALLOWED_EXTENSIONS"]),
        },
    }), 200


@api_bp.route("/skills", methods=["GET"])
def list_skills():
    """Return available skills with optional filtering."""
    query = (request.args.get("q") or "").strip().lower()
    limit = request.args.get("limit", default=200, type=int)
    limit = max(1, min(limit, 1000))

    all_skills = load_skills(current_app.config["SKILLS_FILE"])
    filtered = [skill for skill in all_skills if query in skill.lower()] if query else all_skills
    filtered = sorted(filtered, key=str.lower)[:limit]

    return jsonify({
        "count": len(filtered),
        "total": len(all_skills),
        "skills": filtered,
        "by_category": group_by_category(filtered, current_app.config["SKILLS_FILE"]),
    }), 200


@api_bp.route("/analyze", methods=["POST"])
def analyze_resume():
    """Analyze an uploaded resume and return structured JSON insights."""
    if "resume" not in request.files:
        return jsonify({"error": "No resume file provided. Use form-data key 'resume'."}), 400

    file = request.files["resume"]
    filename = file.filename or ""
    if not filename:
        return jsonify({"error": "Empty filename. Please choose a resume file."}), 400
    if not allowed_file(filename):
        return jsonify({"error": "Unsupported file type. Allowed: PDF, DOCX, TXT, PNG, JPG, JPEG, WEBP."}), 400

    text, error = _read_upload(file)
    if error:
        return jsonify({"error": error}), 400

    job_description = request.form.get("job_description", "").strip()
    return jsonify(build_analysis_payload(text, job_description)), 200


@api_bp.route("/analyze/text", methods=["POST"])
def analyze_resume_text():
    """Analyze raw resume text directly (no file upload required)."""
    payload = request.get_json(silent=True) or {}
    resume_text = (payload.get("resume_text") or "").strip()
    if not resume_text:
        return jsonify({"error": "Provide non-empty 'resume_text' in JSON body."}), 400

    job_description = (payload.get("job_description") or "").strip()
    use_llm = payload.get("use_ai", True)
    return jsonify(build_analysis_payload(resume_text, job_description, use_llm=bool(use_llm))), 200


@api_bp.route("/ats-check", methods=["POST"])
def ats_check():
    """Run ATS checks on plain resume text and return checklist results."""
    payload = request.get_json(silent=True) or {}
    resume_text = (payload.get("resume_text") or "").strip()
    if not resume_text:
        return jsonify({"error": "Provide non-empty 'resume_text' in JSON body."}), 400

    skills_file = current_app.config["SKILLS_FILE"]
    skill_analysis = detect_skills(resume_text, skills_file)
    structure = analyze_resume_structure(resume_text)
    return jsonify(run_ats_checker(resume_text, skill_analysis["detected_skills"], structure)), 200


@api_bp.route("/report/download", methods=["POST"])
def download_report():
    """Accept analysis JSON and return a generated PDF report."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not payload:
        return jsonify({"error": "Provide analysis JSON body to generate report."}), 400

    try:
        pdf_data = build_report_pdf(payload)
    except Exception as exc:
        return jsonify({"error": f"Could not build report: {exc}"}), 400

    return send_file(
        BytesIO(pdf_data),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="resume-analysis-report.pdf",
    )


@api_bp.route("/bulk-analyze", methods=["POST"])
def bulk_analyze_resumes():
    """Analyze multiple resumes at once for recruiter use."""
    if "resumes" not in request.files:
        return jsonify({"error": "No resumes provided. Use form-data key 'resumes'."}), 400

    files = [f for f in request.files.getlist("resumes") if f and f.filename]
    if not files:
        return jsonify({"error": "At least one resume is required."}), 400

    max_batch = current_app.config["MAX_BULK_FILES"]
    if len(files) > max_batch:
        return jsonify({"error": f"Too many files. Upload at most {max_batch} resumes per batch."}), 400

    job_description = request.form.get("job_description", "").strip()
    skills_file = current_app.config["SKILLS_FILE"]

    results = []
    failures = []

    for file in files:
        filename = file.filename or ""
        if not allowed_file(filename):
            failures.append({"filename": filename, "error": "Unsupported format."})
            continue

        text, error = _read_upload(file)
        if error:
            failures.append({"filename": filename, "error": error})
            continue

        try:
            skill_analysis = detect_skills(text, skills_file, job_description)
            jd_score = None
            if job_description:
                jd_score = compare_with_job_description(text, job_description, skills_file)[
                    "job_description_match_score"
                ]

            structure = analyze_resume_structure(text)
            ats = run_ats_checker(text, skill_analysis["detected_skills"], structure)
            comprehensive = calculate_comprehensive_score(
                skill_analysis, text, jd_score, structure, ats
            )

            results.append({
                "filename": filename,
                "overall_score": comprehensive["overall_score"],
                "score_breakdown": comprehensive["score_breakdown"],
                "detected_skills": skill_analysis["detected_skills"],
                "missing_skills": skill_analysis["missing_skills"],
                "required_skills": skill_analysis["required_skills"],
                "ats_score": ats["ats_score"],
                "jd_match_score": jd_score,
                "quality_metrics": comprehensive["quality_metrics"],
                "success": True,
            })
        except Exception as exc:
            current_app.logger.exception("Bulk analysis failed for %s", filename)
            failures.append({"filename": filename, "error": str(exc)})

    return jsonify({
        "total_analyzed": len(results),
        "ranked_candidates": compare_candidates(results),
        "failed_count": len(failures),
        "failures": failures,
        "job_description": job_description or None,
    }), 200


@api_bp.route("/import/profile", methods=["POST"])
def import_profile():
    """Turn a LinkedIn PDF export or an existing CV into CV Maker fields.

    Accepts a file upload (form key 'profile') or raw text (JSON 'text').
    A LinkedIn profile URL cannot be fetched: the page serves an authwall to
    anyone not signed in, and LinkedIn's robots.txt prohibits automated access.
    A URL therefore comes back with instructions rather than a silent failure.
    """
    text = ""

    if "profile" in request.files:
        file = request.files["profile"]
        if not file.filename:
            return jsonify({"error": "Empty filename. Choose a file."}), 400
        if not allowed_file(file.filename):
            return jsonify({
                "error": "Unsupported file type. Upload the PDF you saved from LinkedIn, "
                         "or a CV in PDF, DOCX or TXT."
            }), 400
        text, error = _read_upload(file)
        if error:
            return jsonify({"error": error}), 400
    else:
        payload = request.get_json(silent=True) or {}
        text = (payload.get("text") or "").strip()

    if not text:
        return jsonify({"error": "Provide a file, or paste your profile text."}), 400

    # A bare profile URL is the one input that cannot work. Say why, and say
    # exactly what to do instead, rather than returning an empty profile.
    stripped = text.strip()
    if len(stripped) < 400 and re.match(r"^(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/", stripped, re.I):
        return jsonify({
            "error": "LinkedIn profile pages cannot be read from a link.",
            "reason": (
                "LinkedIn shows a sign-in wall to anything that is not a logged-in "
                "browser, and its terms prohibit automated access. Nothing can read "
                "your profile from the URL alone."
            ),
            "how_to_fix": [
                "Open your LinkedIn profile.",
                "Click 'More' under your headline, then 'Save to PDF'.",
                "Drop that PDF here. It contains everything this needs.",
            ],
            "alternative": (
                "Or open your profile, select all the text with Ctrl+A, and paste it below."
            ),
        }), 422

    result = parse_profile(text)
    if result["fields_found"] == 0:
        return jsonify({
            "error": "Nothing recognisable was found in that text.",
            "warnings": result["warnings"],
        }), 422

    # Score the imported profile immediately: knowing it parsed is less useful
    # than knowing whether it is any good.
    skills_file = current_app.config["SKILLS_FILE"]
    detected = detect_skills(text, skills_file)["detected_skills"]

    return jsonify({
        "source": result["source"],
        "fields_found": result["fields_found"],
        "warnings": result["warnings"],
        "profile": result["profile"],
        "recognised_skills": detected,
        "recognised_skills_by_category": group_by_category(detected, skills_file),
    }), 200


@api_bp.route("/candidate-report", methods=["POST"])
def generate_candidate_detailed_report():
    """Generate a detailed candidate report with insights and recommendations."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not payload:
        return jsonify({"error": "Provide candidate analysis data."}), 400

    analysis = {
        "overall_score": payload.get("overall_score", 0),
        "score_breakdown": payload.get("score_breakdown", {}),
    }
    return jsonify(generate_candidate_report(analysis, payload.get("candidate_name", "Candidate"))), 200


@api_bp.route("/rewrite-cv", methods=["POST"])
def rewrite_cv():
    """Rewrite summary and experience bullets to align with a target job."""
    payload = request.get_json(silent=True) or {}
    summary = (payload.get("summary") or "").strip()
    experience = payload.get("experience") or []
    job_description = (payload.get("job_description") or "").strip()

    if not job_description:
        return jsonify({"error": "Provide a non-empty 'job_description'."}), 400
    if not isinstance(experience, list):
        return jsonify({"error": "'experience' must be a list."}), 400

    skills_file = current_app.config["SKILLS_FILE"]
    combined = summary + "\n" + "\n".join(
        str(item.get("description", "")) for item in experience if isinstance(item, dict)
    )

    analysis = compare_with_job_description(combined, job_description, skills_file)
    missing_skills = analysis.get("missing_skills", [])
    missing_terms = analysis.get("missing_jd_keywords", [])
    targets = (missing_skills or missing_terms)[:8]

    # Prefer a real model rewrite when one is configured; fall back to
    # deterministic guidance that tells the user exactly what to add rather
    # than pasting keyword soup into their CV.
    enriched = llm.enrich_analysis(current_app.config, combined, job_description, [])
    if enriched and enriched.get("rewrite_suggestions"):
        return jsonify({
            "source": "ai",
            "model": enriched.get("model"),
            "rewritten_summary": enriched.get("summary") or summary,
            "rewrite_suggestions": enriched["rewrite_suggestions"],
            "missing_skills": missing_skills,
            "suggestions": [
                "Each rewrite below keeps your facts and adds structure. "
                "Replace any [X%] placeholder with your real number before using it.",
            ],
        }), 200

    suggestions = [
        "Start each bullet with an action verb and end it with a measurable outcome.",
        "Use two to four hard numbers across the summary and experience: percentage, "
        "amount, volume, or time saved.",
        "Mirror the job's own vocabulary only where it genuinely describes your work.",
    ]
    if targets:
        suggestions.insert(0, "This role asks for, and your CV does not evidence: " + ", ".join(targets))

    return jsonify({
        "source": "rules",
        "rewritten_summary": summary,
        "rewrite_suggestions": [],
        "missing_skills": missing_skills,
        "suggestions": suggestions,
        "note": (
            "Automatic rewriting needs a language model. Set LLM_ENABLED=true and point "
            "LLM_BASE_URL at a local Ollama instance to enable it. The guidance above is "
            "generated from your CV and the job description without one."
        ),
    }), 200
