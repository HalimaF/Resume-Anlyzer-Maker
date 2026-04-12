from pathlib import Path
from io import BytesIO
from tempfile import gettempdir
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request, send_file

from .services.analyzer import (
    analyze_resume_structure,
    calculate_resume_score,
    compare_with_job_description,
    detect_skills,
    keyword_frequency,
    load_skills,
    run_ats_checker,
)
from .services.extractor import extract_resume_text
from .services.feedback import generate_feedback
from .services.report_generator import build_report_pdf
from .services.scoring import calculate_comprehensive_score, compare_candidates, generate_candidate_report

api_bp = Blueprint("api", __name__)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


@api_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "service": "smart-resume-analyzer"}), 200


@api_bp.route("/skills", methods=["GET"])
def list_skills():
    """Return available skills with optional filtering."""
    query = (request.args.get("q") or "").strip().lower()
    limit = request.args.get("limit", default=200, type=int)
    limit = max(1, min(limit, 500))

    all_skills = load_skills(current_app.config["SKILLS_FILE"])
    if query:
        filtered = [skill for skill in all_skills if query in skill.lower()]
    else:
        filtered = all_skills

    filtered = sorted(filtered, key=str.lower)[:limit]
    return jsonify({"count": len(filtered), "skills": filtered}), 200


@api_bp.route("/analyze", methods=["POST"])
def analyze_resume():
    """Analyze uploaded resume and return structured JSON insights."""
    if "resume" not in request.files:
        return jsonify({"error": "No resume file provided. Use form-data key 'resume'."}), 400

    file = request.files["resume"]
    filename = file.filename or ""
    if filename == "":
        return jsonify({"error": "Empty filename. Please choose a resume file."}), 400

    if not allowed_file(filename):
        return jsonify({"error": "Unsupported file type. Allowed: PDF, DOCX, TXT, PNG, JPG, JPEG, WEBP."}), 400

    job_description = request.form.get("job_description", "").strip()

    suffix = Path(filename).suffix or ".pdf"
    temp_dir = Path(gettempdir()) / "resume_analyzer_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid4().hex}{suffix}"

    try:
        file.save(temp_path)
        extracted_text = extract_resume_text(temp_path)
    except Exception as exc:
        return jsonify({"error": f"Failed to extract resume text: {exc}"}), 500
    finally:
        # Cleanup is best-effort so failed deletions do not break API responses.
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass

    if not extracted_text:
        return jsonify({"error": "No readable text found in the uploaded resume."}), 400

    skills_list = load_skills(current_app.config["SKILLS_FILE"])
    skill_analysis = detect_skills(extracted_text, skills_list)

    jd_data = None
    jd_score = None
    if job_description:
        jd_data = compare_with_job_description(extracted_text, job_description)
        jd_score = jd_data["job_description_match_score"]

    resume_score = calculate_resume_score(skill_analysis, extracted_text, jd_score)

    structure_analysis = analyze_resume_structure(extracted_text)

    response_payload = {
        "resume_score": resume_score,
        "detected_skills": skill_analysis["detected_skills"],
        "missing_skills": skill_analysis["missing_skills"],
        "top_keywords": keyword_frequency(extracted_text),
        "structure_analysis": structure_analysis,
        "ats_check": run_ats_checker(extracted_text, skill_analysis["detected_skills"]),
        "feedback": {},
        "job_description_analysis": jd_data,
        "meta": {
            "detected_skill_count": len(skill_analysis["detected_skills"]),
            "missing_skill_count": len(skill_analysis["missing_skills"]),
        },
    }

    response_payload["feedback"] = generate_feedback(response_payload)

    return jsonify(response_payload), 200


@api_bp.route("/analyze/text", methods=["POST"])
def analyze_resume_text():
    """Analyze raw resume text directly (no file upload required)."""
    payload = request.get_json(silent=True) or {}
    resume_text = (payload.get("resume_text") or "").strip()
    if not resume_text:
        return jsonify({"error": "Provide non-empty 'resume_text' in JSON body."}), 400

    job_description = (payload.get("job_description") or "").strip()
    skills_list = load_skills(current_app.config["SKILLS_FILE"])
    skill_analysis = detect_skills(resume_text, skills_list)

    jd_data = None
    jd_score = None
    if job_description:
        jd_data = compare_with_job_description(resume_text, job_description)
        jd_score = jd_data["job_description_match_score"]

    response_payload = {
        "resume_score": calculate_resume_score(skill_analysis, resume_text, jd_score),
        "detected_skills": skill_analysis["detected_skills"],
        "missing_skills": skill_analysis["missing_skills"],
        "top_keywords": keyword_frequency(resume_text),
        "structure_analysis": analyze_resume_structure(resume_text),
        "ats_check": run_ats_checker(resume_text, skill_analysis["detected_skills"]),
        "feedback": {},
        "job_description_analysis": jd_data,
        "meta": {
            "detected_skill_count": len(skill_analysis["detected_skills"]),
            "missing_skill_count": len(skill_analysis["missing_skills"]),
        },
    }
    response_payload["feedback"] = generate_feedback(response_payload)
    return jsonify(response_payload), 200


@api_bp.route("/ats-check", methods=["POST"])
def ats_check():
    """Run ATS checks on plain resume text and return checklist results."""
    payload = request.get_json(silent=True) or {}
    resume_text = (payload.get("resume_text") or "").strip()
    if not resume_text:
        return jsonify({"error": "Provide non-empty 'resume_text' in JSON body."}), 400

    skills_list = load_skills(current_app.config["SKILLS_FILE"])
    skill_analysis = detect_skills(resume_text, skills_list)
    ats_result = run_ats_checker(resume_text, skill_analysis["detected_skills"])
    return jsonify(ats_result), 200


@api_bp.route("/report/download", methods=["POST"])
def download_report():
    """Accept analysis JSON and return a generated PDF report."""
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Provide analysis JSON body to generate report."}), 400

    pdf_data = build_report_pdf(payload)
    return send_file(
        BytesIO(pdf_data),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="resume-analysis-report.pdf",
    )


@api_bp.route("/bulk-analyze", methods=["POST"])
def bulk_analyze_resumes():
    """Analyze multiple resumes at once for company/recruiter use."""
    if "resumes" not in request.files:
        return jsonify({"error": "No resumes provided. Use form-data key 'resumes[]'."}), 400

    files = request.files.getlist("resumes")
    if not files or len(files) == 0:
        return jsonify({"error": "At least one resume is required."}), 400

    job_description = request.form.get("job_description", "").strip()
    results = []
    skills_list = load_skills(current_app.config["SKILLS_FILE"])

    for file in files:
        if not file or file.filename == "":
            continue

        filename = file.filename or ""
        if not allowed_file(filename):
            results.append({
                "filename": filename,
                "error": f"Unsupported format. Allowed: PDF, DOCX, TXT, PNG, JPG, JPEG, WEBP"
            })
            continue

        suffix = Path(filename).suffix or ".pdf"
        temp_dir = Path(gettempdir()) / "resume_analyzer_uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"{uuid4().hex}{suffix}"

        try:
            file.save(temp_path)
            extracted_text = extract_resume_text(temp_path)

            if not extracted_text:
                results.append({
                    "filename": filename,
                    "error": "No readable text found"
                })
                continue

            skill_analysis = detect_skills(extracted_text, skills_list)
            jd_data = None
            jd_score = None
            
            if job_description:
                jd_data = compare_with_job_description(extracted_text, job_description)
                jd_score = jd_data["job_description_match_score"]

            structure = analyze_resume_structure(extracted_text)
            ats = run_ats_checker(extracted_text, skill_analysis["detected_skills"])
            base_score = calculate_resume_score(skill_analysis, extracted_text, jd_score)

            comprehensive = calculate_comprehensive_score(skill_analysis, extracted_text, jd_score, structure, ats)

            results.append({
                "filename": filename,
                "overall_score": comprehensive["overall_score"],
                "score_breakdown": comprehensive["score_breakdown"],
                "detected_skills": skill_analysis["detected_skills"],
                "missing_skills": skill_analysis["missing_skills"],
                "ats_score": ats["ats_score"],
                "jd_match_score": jd_score or None,
                "quality_metrics": comprehensive["quality_metrics"],
                "success": True
            })

        except Exception as exc:
            results.append({
                "filename": filename,
                "error": str(exc)
            })
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    # Sort by score descending
    successful_results = [r for r in results if r.get("success")]
    ranked = compare_candidates(successful_results)

    return jsonify({
        "total_analyzed": len(successful_results),
        "ranked_candidates": ranked,
        "failed_count": len(results) - len(successful_results),
        "job_description": job_description if job_description else None
    }), 200


@api_bp.route("/candidate-report", methods=["POST"])
def generate_candidate_detailed_report():
    """Generate detailed candidate report with insights and recommendations."""
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Provide candidate analysis data"}), 400

    candidate_name = payload.get("candidate_name", "Candidate")
    overall_score = payload.get("overall_score", 0)
    
    # Build analysis dict from payload
    analysis = {
        "overall_score": overall_score,
        "score_breakdown": payload.get("score_breakdown", {})
    }

    report = generate_candidate_report(analysis, candidate_name)
    return jsonify(report), 200


@api_bp.route("/semantic-search", methods=["POST"])
def semantic_search():
    """Semantic search for candidates matching job requirements using skill context."""
    payload = request.get_json(silent=True) or {}
    candidates = payload.get("candidates", [])
    job_description = payload.get("job_description", "").strip()

    if not candidates or not job_description:
        return jsonify({"error": "Provide candidates list and job description"}), 400

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    try:
        vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 3), lowercase=True)
        
        # Prepare documents
        documents = [job_description] + [c.get("text", "") for c in candidates]
        
        # Fit and transform
        matrix = vectorizer.fit_transform(documents)
        
        # Calculate similarity of each candidate to job description
        job_vector = matrix[0]
        similarities = cosine_similarity(job_vector, matrix[1:])[0]
        
        # Score candidates
        scored_candidates = []
        for idx, candidate in enumerate(candidates):
            score = min(int(similarities[idx] * 100), 100)
            scored_candidates.append({
                "candidate": candidate.get("name", f"Candidate {idx+1}"),
                "semantic_match_score": score,
                "match_percentage": f"{score}%"
            })
        
        # Sort by score
        scored_candidates.sort(key=lambda x: x["semantic_match_score"], reverse=True)
        
        return jsonify({
            "results": scored_candidates,
            "method": "semantic_search",
            "total_candidates": len(scored_candidates)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Semantic search failed: {str(e)}"}), 500


@api_bp.route("/rewrite-cv", methods=["POST"])
def rewrite_cv():
    """Rewrite summary and experience bullets to align better with a target job description."""
    payload = request.get_json(silent=True) or {}
    summary = (payload.get("summary") or "").strip()
    experience = payload.get("experience") or []
    job_description = (payload.get("job_description") or "").strip()

    if not job_description:
        return jsonify({"error": "Provide non-empty 'job_description'."}), 400

    if not isinstance(experience, list):
        return jsonify({"error": "'experience' must be a list."}), 400

    try:
        analysis = compare_with_job_description(f"{summary}\n" + "\n".join(
            [str(item.get("description", "")) for item in experience if isinstance(item, dict)]
        ), job_description)
        high_value_terms = analysis.get("missing_jd_keywords", [])[:8]

        rewritten_summary = summary
        if summary:
            base = summary.rstrip(".")
            if high_value_terms:
                rewritten_summary = (
                    f"{base}. Tailored for roles requiring {', '.join(high_value_terms[:4])}, "
                    "with a focus on measurable impact, ownership, and cross-functional delivery."
                )

        rewritten_experience = []
        for idx, item in enumerate(experience):
            if not isinstance(item, dict):
                rewritten_experience.append({"description": ""})
                continue

            original_desc = str(item.get("description") or "").strip()
            role_terms = high_value_terms[idx % len(high_value_terms): (idx % len(high_value_terms)) + 2] if high_value_terms else []

            if original_desc:
                rewritten_desc = original_desc
                if role_terms:
                    rewritten_desc += (
                        f" Focused on {', '.join(role_terms)} with clear outcomes and quantifiable results."
                    )
            else:
                rewritten_desc = (
                    "Delivered business-impacting work with clear ownership, cross-team collaboration, "
                    "and measurable improvements in quality, speed, or reliability."
                )

            rewritten_experience.append({"description": rewritten_desc})

        suggestions = [
            "Use 2-4 metrics across summary and experience (%, time saved, revenue, scale).",
            "Mirror key job terms naturally in section headings and bullet points.",
            "Start bullets with strong action verbs and end with measurable impact.",
        ]
        if high_value_terms:
            suggestions.insert(0, "Prioritize these target keywords: " + ", ".join(high_value_terms[:6]))

        return jsonify(
            {
                "rewritten_summary": rewritten_summary,
                "rewritten_experience": rewritten_experience,
                "suggestions": suggestions,
            }
        ), 200
    except Exception as exc:
        return jsonify({"error": f"Rewrite failed: {exc}"}), 500
