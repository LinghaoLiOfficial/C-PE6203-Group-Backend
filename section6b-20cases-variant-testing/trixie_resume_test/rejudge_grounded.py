"""Re-score the already-generated A/B/C outputs with a grounding-gated judge
prompt: any fabricated skill/employer/metric caps that variant's other scores.
Reuses variant_comparison_results.json outputs (no new generation calls) so
only the judge step is repeated with a stricter rubric.

Run from anywhere: python rejudge_grounded.py
Requires the backend's venv and its .env (reads DB + LLM config).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2] / "C-PE6203-Group-Backend"
sys.path.insert(0, str(BACKEND_ROOT))

import httpx

from app.core.config import settings

RESULTS_PATH = Path(__file__).resolve().parent / "variant_comparison_results.json"
OUT_PATH = Path(__file__).resolve().parent / "variant_comparison_results_grounded_judge.json"

CRITERIA = [
    ("grounding", "Grounding / No Fabrication", "Does the output rely only on facts present in the source resume, with no invented employers, dates, metrics, or skills?"),
    ("personalization", "Personalization / Relevance", "Does it appropriately tailor emphasis to the target job, without force-fitting irrelevant claims?"),
    ("correctness", "Correctness & Completeness", "Are the facts accurate and is nothing materially important from the source dropped or altered?"),
    ("clarity", "Clarity & Change Evidence", "Is the output well-structured and does it explain what changed and why, traceable to source evidence?"),
]

JUDGE_SYSTEM = (
    "You are a strict, impartial evaluator of AI-generated tailored resumes. "
    "You compare three candidate outputs (A, B, C) against a source resume and a target job description.\n\n"
    "HARD RULE (apply before scoring anything else): scan each variant for ANY skill, tool, employer, "
    "job title, metric, date, or credential that is not explicitly present in the source resume. "
    "If you find even one fabricated item in a variant:\n"
    "  - that variant's grounding score MUST be 1\n"
    "  - that variant's personalization, correctness, and clarity scores MUST each be capped at 2, "
    "even if the writing is fluent or well-organized\n"
    "Fluent, confident, well-organized prose built on fabricated facts is a FAILURE, not a good result. "
    "Do not reward eloquence over truthfulness. "
    "Only a variant with zero fabricated content is eligible for scores above 2 on any criterion.\n\n"
    "Return ONLY a JSON object, no markdown, no commentary."
)


def call_llm(system_prompt: str, user_prompt: str, *, max_tokens: int = 1600) -> str:
    resp = httpx.post(
        settings.llm_base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        json={
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        },
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def judge(resume_text: str, job_description: str, outputs: dict) -> dict:
    criteria_desc = "\n".join(f"- {key}: {label} — {desc}" for key, label, desc in CRITERIA)
    user_prompt = (
        f"Source resume:\n{resume_text}\n\n"
        f"Target job description:\n{job_description}\n\n"
        f"Variant A output:\n{outputs['A']}\n\n"
        f"Variant B output:\n{outputs['B']}\n\n"
        f"Variant C output:\n{json.dumps(outputs['C'], ensure_ascii=False)}\n\n"
        f"Criteria:\n{criteria_desc}\n\n"
        "First, list any fabricated items you find per variant (empty list if none). "
        "Then return JSON exactly in this shape:\n"
        "{\n"
        '  "fabrications": {"A": [""], "B": [""], "C": [""]},\n'
        '  "A": {' + ", ".join(f'"{k}": {{"score": 0, "reason": ""}}' for k, _, _ in CRITERIA) + "},\n"
        '  "B": {' + ", ".join(f'"{k}": {{"score": 0, "reason": ""}}' for k, _, _ in CRITERIA) + "},\n"
        '  "C": {' + ", ".join(f'"{k}": {{"score": 0, "reason": ""}}' for k, _, _ in CRITERIA) + "}\n"
        "}\n"
        "Scores are integers 1-5, obeying the HARD RULE from the system prompt."
    )
    for max_tokens in (1600, 2500, 3500):
        raw = call_llm(JUDGE_SYSTEM, user_prompt, max_tokens=max_tokens)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            print(f"  (judge JSON truncated/malformed at max_tokens={max_tokens}, retrying with more tokens)")
            continue
    raise RuntimeError(f"Judge never returned valid JSON. Last raw response:\n{raw}")


def main() -> None:
    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    resume_text_cache = {}
    out = []
    for entry in data:
        print(f"=== {entry['job_title']} @ {entry['company_name']} ===")
        # resume text isn't stored per-entry in the original file; re-fetch once via DB
        if not resume_text_cache:
            from app.db.session import SessionLocal
            from app.models.user import User
            from app.models.resume import Resume
            db = SessionLocal()
            user = db.query(User).filter(User.email == "trixgracemok@gmail.com").first()
            resume = db.query(Resume).filter(Resume.user_id == user.id, Resume.is_active.is_(True)).first()
            if resume is None:
                resume = db.query(Resume).filter(Resume.user_id == user.id).first()
            resume_text_cache["text"] = resume.parsed_text
            db.close()
        resume_text = resume_text_cache["text"]

        scores = judge(resume_text, entry["job_description"], entry["outputs"])
        entry_out = dict(entry)
        entry_out["grounded_judge_scores"] = scores
        out.append(entry_out)
        OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print("  done")

    print(f"\nSaved to {OUT_PATH}")


if __name__ == "__main__":
    main()
