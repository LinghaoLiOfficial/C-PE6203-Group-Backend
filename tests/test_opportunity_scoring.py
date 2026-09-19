"""Regression tests for opportunity-fit scoring.

Written from the F4 retest failure: candidate T01 Jordan (JavaScript/React/REST
APIs/Node.js) and T07 Clara (no overlap) both scored 0% fit on the same Node.js
Developer role.

Root cause: the two sides of the skill comparison are produced by different code
paths and were never normalised onto one vocabulary.

  * Job requirements come from a keyword scan of the posting against a fixed set
    that did not contain node/nodejs/express/mongodb/redis, so a Node.js posting
    yielded required_skills == [].
  * Candidate skills come from the resume parser, which is free-form in LLM mode
    ("Node.js", "REST APIs") and keyword-based in fallback mode ("rest").

An empty or non-overlapping intersection drives attainability to 0, and the
multiplicative gate then returns fit == 0 for every candidate, so a well-matched
and a zero-overlap candidate become indistinguishable.

These tests pin the behaviour we want: comparable skills must be recognised as
equal, and a posting with nothing to compare against must say so rather than
assert a confident zero.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.career_intelligence import CandidateGraph, JobMarketProfile
from app.models.job import Job
from app.models.resume import Resume
from app.services.job_portal_service import JobPortalService

NODE_JD = (
    "Node.js Developer. Build scalable services with Node.js and Express.js. "
    "Experience with MongoDB and Redis is a plus. 3+ years experience."
)
BACKEND_JD = (
    "Backend Engineer. Build FastAPI services with Python and PostgreSQL, "
    "expose REST APIs, and ship with Docker. 3+ years experience."
)
NO_SKILL_JD = (
    "Warehouse Assistant. Reliable and physically fit team member to support "
    "daily inbound and outbound operations. 1+ years experience."
)


def _make_resume(db: Session, user_id: UUID, name: str, skills: list[str]) -> Resume:
    resume = Resume(
        user_id=user_id,
        file_name=f"{name}.pdf",
        file_url=f"storage/resumes/{name}.pdf",
        parsed_text=f"{name} resume",
        extracted_skills=skills,
        is_active=True,
    )
    db.add(resume)
    db.flush()
    db.add(
        CandidateGraph(
            user_id=user_id,
            resume_id=resume.id,
            summary="",
            skills=[{"name": skill, "evidence": [{"source": "resume", "text": skill}]} for skill in skills],
            experiences=[],
            education=[],
            projects=[],
            achievements=[],
            publications=[],
            constraints={},
            preferences={},
            source_spans=[],
            user_confirmed=False,
        )
    )
    db.flush()
    return resume


def _make_job(db: Session, svc: JobPortalService, title: str, description: str, external_id: str) -> Job:
    job = Job(
        job_title=title,
        job_description=description,
        source="csv",
        external_id=external_id,
        external_apply_url="https://example.com/jobs/x",
        skill_tags=svc._extract_skills(description),
        is_active=True,
    )
    db.add(job)
    db.flush()
    payload = svc._extract_job_requirements(title, description)
    db.add(
        JobMarketProfile(
            job_id=job.id,
            occupation_family=str(payload["occupation_family"]),
            seniority=str(payload["seniority"]),
            required_skills=list(payload["required_skills"]),
            preferred_skills=list(payload["preferred_skills"]),
            education_requirements=list(payload["education_requirements"]),
            experience_requirements=list(payload["experience_requirements"]),
            licenses=list(payload["licenses"]),
            salary_confidence=str(payload["salary_confidence"]),
            freshness_score=float(payload["freshness_score"]),
            trust_score=float(payload["trust_score"]),
            raw_requirements=payload,
        )
    )
    db.flush()
    return job


def _report(label: str, svc: JobPortalService, job: Job, resume: Resume, user_id: UUID):
    match = svc._score_job(user_id, job, resume)
    print(
        f"    {label:42s} fit={match.score:.3f}  attainability={match.vector.attainability:.3f}  "
        f"exact={len(match.exact_skills)} required={len(match.required_skills)} "
        f"missing={len(match.missing_skills)} category={match.category}"
    )
    return match


def test_node_role_distinguishes_matched_from_unmatched(db_session: Session, test_user) -> None:
    """Jordan must outscore Clara on a Node.js role, whatever spelling the parser used."""
    svc = JobPortalService(db_session)
    node_job = _make_job(db_session, svc, "Node.js Developer", NODE_JD, "f4-node")

    # Free-form shapes, as the LLM parser emits them.
    jordan = _make_resume(db_session, test_user.id, "jordan", ["Node.js", "Express.js", "REST APIs", "React"])
    # The same four skills spelled the way a different parser would emit them. These
    # must score identically, or the comparison is really a spelling test.
    jordan_alt = _make_resume(
        db_session, test_user.id, "jordan_alt", ["nodejs", "express js", "restful", "react.js"]
    )
    # Keyword shapes, as the heuristic fallback emits them.
    jordan_fallback = _make_resume(
        db_session, test_user.id, "jordan_fb", ["node.js", "express", "rest", "react"]
    )
    clara = _make_resume(db_session, test_user.id, "clara", ["Excel", "Sales"])

    print("\n  --- Node.js Developer ---")
    m_rich = _report("Jordan (LLM free-form skills)", svc, node_job, jordan, test_user.id)
    m_alt = _report("Jordan (same skills, other spellings)", svc, node_job, jordan_alt, test_user.id)
    m_fallback = _report("Jordan (heuristic fallback skills)", svc, node_job, jordan_fallback, test_user.id)
    m_poor = _report("Clara  (excel/sales)", svc, node_job, clara, test_user.id)

    assert node_job.skill_tags, "the Node.js posting must yield extractable requirements"
    assert m_poor.score == 0.0, "a zero-overlap candidate must still score zero"
    assert m_rich.score > m_poor.score, "a matched candidate must outscore an unmatched one"
    assert m_rich.score == m_alt.score, "spelling must not change the score"
    assert m_rich.score == m_fallback.score, "parser vocabulary must not change the score"


def test_gate_still_discriminates_when_requirements_resolve(db_session: Session, test_user) -> None:
    """Control: the multiplicative gate keeps working on a resolvable posting."""
    svc = JobPortalService(db_session)
    backend_job = _make_job(db_session, svc, "Backend Engineer", BACKEND_JD, "f4-backend")

    strong = _make_resume(
        db_session, test_user.id, "strong", ["Python", "PostgreSQL", "REST APIs", "Docker"]
    )
    weak = _make_resume(db_session, test_user.id, "weak", ["Excel", "Sales"])

    print("\n  --- Backend Engineer (control) ---")
    m_strong = _report("strong (python/postgresql/rest/docker)", svc, backend_job, strong, test_user.id)
    m_weak = _report("weak   (excel/sales)", svc, backend_job, weak, test_user.id)

    # The posting names FastAPI as well, which this candidate does not have, so a
    # near-total match is the expected ceiling rather than a perfect one.
    assert m_strong.vector.attainability >= 0.8
    assert m_strong.score > m_weak.score


def test_posting_without_requirements_does_not_assert_zero(db_session: Session, test_user) -> None:
    """With nothing to compare against, the score must not claim the candidate is unqualified."""
    svc = JobPortalService(db_session)
    job = _make_job(db_session, svc, "Warehouse Assistant", NO_SKILL_JD, "f4-noskill")
    candidate = _make_resume(db_session, test_user.id, "anyone", ["Excel", "Sales"])

    print("\n  --- Warehouse Assistant (no extractable requirements) ---")
    match = _report("any candidate", svc, job, candidate, test_user.id)

    assert match.required_skills == []
    assert match.score > 0.0, "missing requirement data must not be reported as a zero fit"
    assert any("requirements" in line for line in match.rationale), (
        "the rationale must disclose that the posting had no structured requirements"
    )
    assert match.data_confidence <= 0.4, "a score without comparison data must be low confidence"


# --- Reconstructed from the Section 6a T01 evidence -------------------------------
# The captured job detail for "Node js developer" (HyperNova Consulting) shows
# attainability 0% and entry barrier 100% while the same panel lists
# "Required skills: aws, javascript, react, rest", and every one of the 24 roles on
# the opportunity map is marked "high transition" -- i.e. the score matched nothing
# against anything. The parsed result for the same candidate lists 12 skills.
NODE_POSTING_REQUIRED = ["aws", "javascript", "react", "rest"]
JORDAN_PARSED_SKILLS = [
    "JavaScript",
    "TypeScript",
    "SQL",
    "Node.js",
    "Express.js",
    "REST APIs",
    "JWT authentication",
    "PostgreSQL",
    "Redis",
    "React",
    "Docker",
    "Jest",
]


def _make_job_with_requirements(
    db: Session, title: str, required: list[str], external_id: str
) -> Job:
    job = Job(
        job_title=title,
        job_description="Node js developer",
        company_name="HyperNova Consulting",
        location="Singapore, Singapore",
        mid_salary_sgd=110500.0,
        pay_period="yearly",
        source="csv",
        external_id=external_id,
        external_apply_url="https://example.com/jobs/x",
        skill_tags=list(required),
        is_active=True,
    )
    db.add(job)
    db.flush()
    db.add(
        JobMarketProfile(
            job_id=job.id,
            occupation_family="Engineering",
            seniority="mid",
            required_skills=list(required),
            preferred_skills=[],
            freshness_score=1.0,
            trust_score=0.8,
        )
    )
    db.flush()
    return job


def test_t01_jordan_scores_on_the_node_posting_from_the_captured_evidence(
    db_session: Session, test_user
) -> None:
    """The captured T01 case: Jordan's real skills against the posting's real requirements."""
    svc = JobPortalService(db_session)
    job = _make_job_with_requirements(db_session, "Node js developer", NODE_POSTING_REQUIRED, "t01-node")

    jordan = _make_resume(db_session, test_user.id, "jordan_real", JORDAN_PARSED_SKILLS)
    unmatched = _make_resume(db_session, test_user.id, "unmatched", ["Excel", "Sales"])

    print("\n  --- T01: Node js developer (captured requirements) ---")
    m_jordan = _report("Jordan (12 parsed skills)", svc, job, jordan, test_user.id)
    m_unmatched = _report("unmatched (excel/sales)", svc, job, unmatched, test_user.id)

    # Jordan matches javascript, react and "REST APIs" -> rest; only aws is missing.
    assert m_jordan.exact_skills == ["javascript", "react", "rest"]
    assert m_jordan.vector.attainability == 0.75, "the captured case showed 0% attainability"
    assert m_jordan.score > 0.6
    assert m_jordan.category == "easy_win"
    assert m_unmatched.score == 0.0


def test_resume_without_a_candidate_graph_still_scores(db_session: Session, test_user) -> None:
    """A parsed resume with no graph row must not score as a candidate with no skills.

    _get_candidate_graph creates a blank graph on demand, so scoring against it reads
    as "matches nothing" against every posting at once -- which is what an opportunity
    map with 0% attainability on all 24 roles looks like.
    """
    svc = JobPortalService(db_session)
    job = _make_job_with_requirements(db_session, "Node js developer", NODE_POSTING_REQUIRED, "t01-nograph")

    # Same candidate, but deliberately no CandidateGraph row.
    resume = Resume(
        user_id=test_user.id,
        file_name="jordan_no_graph.pdf",
        file_url="storage/resumes/jordan_no_graph.pdf",
        parsed_text="Jordan resume",
        extracted_skills=JORDAN_PARSED_SKILLS,
        is_active=True,
    )
    db_session.add(resume)
    db_session.flush()

    print("\n  --- T01 without a candidate graph row ---")
    match = _report("Jordan (no graph)", svc, job, resume, test_user.id)

    assert match.exact_skills == ["javascript", "react", "rest"]
    assert match.vector.attainability == 0.75
    assert match.score > 0.6
