"""Every role in jobs.json must be answerable by the skill catalog.

Before the catalog was widened, three of seven roles could detect none of their
own requirements: a UX designer or a marketer got a near-zero score no matter
what they uploaded. That failure was invisible until someone tried it, so it is
a test now.
"""

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.services.analyzer import load_skills  # noqa: E402

SKILLS_FILE = BACKEND / "app" / "data" / "skills.json"
JOBS_FILE = BACKEND.parent / "frontend" / "jobs.json"

JOBS = json.loads(JOBS_FILE.read_text(encoding="utf-8"))["jobs"]
CATALOG = set(load_skills(SKILLS_FILE))

VALID_SECTIONS = {"summary", "experience", "education", "projects", "certifications", "skills"}


def test_every_requirement_is_a_canonical_catalog_skill():
    unknown = {
        job["id"]: [s for s in job["keywordRequirements"] if s not in CATALOG]
        for job in JOBS
    }
    unknown = {job_id: missing for job_id, missing in unknown.items() if missing}
    assert not unknown, (
        "These requirements can never be detected, so the role is unusable:\n"
        + "\n".join(f"  {job_id}: {missing}" for job_id, missing in unknown.items())
    )


def test_required_sections_use_the_analyzer_vocabulary():
    invalid = {
        job["id"]: [s for s in job["requiredSections"] if s not in VALID_SECTIONS]
        for job in JOBS
    }
    invalid = {job_id: bad for job_id, bad in invalid.items() if bad}
    assert not invalid, f"Unknown section names: {invalid}"


def test_job_ids_are_unique():
    ids = [job["id"] for job in JOBS]
    assert len(ids) == len(set(ids))


def test_every_job_has_the_fields_the_ui_reads():
    for job in JOBS:
        for key in ("id", "title", "industry", "field", "description",
                    "keywordRequirements", "requiredSections"):
            assert job.get(key), f"{job.get('id', '?')} is missing {key}"
        assert len(job["keywordRequirements"]) >= 6, f"{job['id']} has too few requirements"


def test_roles_span_more_than_technology():
    """The tool claims to serve every profession; the role list must reflect it."""
    fields = {job["field"] for job in JOBS}
    assert len(fields) >= 8, f"Only {len(fields)} fields represented: {sorted(fields)}"
    for expected in ("Healthcare", "Education & Research", "HR & People", "Finance & Legal"):
        assert expected in fields, f"No roles for {expected}"


def test_non_technical_roles_are_fully_detectable():
    """A spot check on the roles that used to detect zero of their own skills."""
    for job_id in ("registered-nurse", "secondary-teacher", "hr-manager",
                   "marketing-manager", "sales-executive", "ux-designer"):
        job = next(j for j in JOBS if j["id"] == job_id)
        detectable = [s for s in job["keywordRequirements"] if s in CATALOG]
        assert len(detectable) == len(job["keywordRequirements"]), job_id
