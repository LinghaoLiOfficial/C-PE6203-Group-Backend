"""One-off script: run A/B/C variant comparison + LLM-judge scoring against
the real running app's tailoring logic (System C), for the Stage 6 report.
Not part of the application - safe to delete after generating the report.

Run from anywhere: python run_variant_comparison.py
Requires the backend's venv (uses its installed packages) and its .env
(reads DB + LLM config via app.core.config.settings).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2] / "C-PE6203-Group-Backend"
sys.path.insert(0, str(BACKEND_ROOT))

import httpx

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.services.job_portal_service import JobPortalService

RESULTS_PATH = Path(__file__).resolve().parent / "variant_comparison_results.json"

JOB_TITLES = [
    "Software Engineer",
    "Machine Learning",
    "DevOps Engineer",
    "Database Administrator",
    "Full Stack Developer",
]

CRITERIA = [
    ("grounding", "Grounding / No Fabrication", "Does the output rely only on facts present in the source resume, with no invented employers, dates, metrics, or skills?"),
    ("personalization", "Personalization / Relevance", "Does the output appropriately tailor emphasis to the target job, without force-fitting irrelevant claims?"),
    ("correctness", "Correctness & Completeness", "Are the facts accurate and is nothing materially important from the source omitted or altered?"),
    ("clarity", "Clarity & Change Evidence", "Is the output well-structured and does it explain what changed and why (traceable to source evidence)?"),
]

JUDGE_SYSTEM = (
    "You are a strict, impartial evaluator of AI-generated tailored resumes. "
    "You compare three candidate outputs (A, B, C) against a source resume and a target job description. "
    "You must be skeptical: penalize any fabricated skill, employer, metric, or experience not present in the source. "
    "Score each variant 1-5 (integer) on each criterion, 1=very poor, 5=excellent. "
    "Return ONLY a JSON object, no markdown, no commentary."
)


def call_llm(system_prompt: str, user_prompt: str, *, json_mode: bool = False, max_tokens: int = 1200) -> str:
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    resp = httpx.post(
        settings.llm_base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        json=payload,
        timeout=90,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def variant_a_minimal(resume_text: str, job_description: str) -> str:
    return call_llm(
        "You are a helpful assistant.",
        f"Rewrite this resume for this job.\n\nResume:\n{resume_text}\n\nJob description:\n{job_description}",
    )


def variant_b_simplified(resume_text: str, job_description: str) -> str:
    return call_llm(
        "You are a resume tailoring assistant.",
        f"Extract relevant skills and tailor this resume to the job.\n\nResume:\n{resume_text}\n\nJob description:\n{job_description}",
    )


def judge(resume_text: str, job_description: str, outputs: dict[str, str]) -> dict:
    criteria_desc = "\n".join(f"- {key}: {label} — {desc}" for key, label, desc in CRITERIA)
    schema_keys = ", ".join(f'"{key}"' for key, _, _ in CRITERIA)
    user_prompt = (
        f"Source resume:\n{resume_text}\n\n"
        f"Target job description:\n{job_description}\n\n"
        f"Variant A output:\n{outputs['A']}\n\n"
        f"Variant B output:\n{outputs['B']}\n\n"
        f"Variant C output:\n{outputs['C']}\n\n"
        f"Criteria:\n{criteria_desc}\n\n"
        "Return JSON exactly in this shape:\n"
        "{\n"
        '  "A": {' + ", ".join(f'"{k}": {{"score": 0, "reason": ""}}' for k, _, _ in CRITERIA) + "},\n"
        '  "B": {' + ", ".join(f'"{k}": {{"score": 0, "reason": ""}}' for k, _, _ in CRITERIA) + "},\n"
        '  "C": {' + ", ".join(f'"{k}": {{"score": 0, "reason": ""}}' for k, _, _ in CRITERIA) + "}\n"
        "}\n"
        "Scores are integers 1-5. Reasons are one short sentence each."
    )
    raw = call_llm(JUDGE_SYSTEM, user_prompt, json_mode=True, max_tokens=1500)
    return json.loads(raw)


def main() -> None:
    db = SessionLocal()
    service = JobPortalService(db)
    user = db.query(User).filter(User.email == "trixgracemok@gmail.com").first()
    resume = db.query(Resume).filter(Resume.user_id == user.id, Resume.is_active.is_(True)).first()
    if resume is None:
        resume = db.query(Resume).filter(Resume.user_id == user.id).first()
    resume_text = resume.parsed_text

    results = []
    for title in JOB_TITLES:
        job = db.query(Job).filter(Job.job_title == title, Job.is_active.is_(True)).first()
        if job is None:
            print(f"SKIP missing job: {title}")
            continue
        print(f"=== {title} @ {job.company_name} ===")
        t0 = time.time()

        print("  running A (minimal)...")
        out_a = variant_a_minimal(resume_text, job.job_description)

        print("  running B (simplified)...")
        out_b = variant_b_simplified(resume_text, job.job_description)

        print("  running C (full system, real app logic)...")
        requirement_summary = service._get_job_requirement_summary(job)
        c_result = service._generate_tailored_resume(resume_text, job.job_description, requirement_summary)
        out_c = c_result.model_dump(mode="json")

        print("  running judge...")
        scores = judge(resume_text, job.job_description, {
            "A": out_a,
            "B": out_b,
            "C": json.dumps(out_c, ensure_ascii=False),
        })

        elapsed = time.time() - t0
        print(f"  done in {elapsed:.1f}s")

        results.append({
            "job_id": str(job.id),
            "job_title": job.job_title,
            "company_name": job.company_name,
            "job_description": job.job_description,
            "outputs": {"A": out_a, "B": out_b, "C": out_c},
            "scores": scores,
            "elapsed_seconds": elapsed,
        })
        RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    db.close()
    print(f"\nSaved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
