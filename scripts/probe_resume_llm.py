from __future__ import annotations

import argparse
import json
import time

from openai import OpenAI
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.llm.json_client import parse_json_object
from app.schemas.ai import ResumeAnalysisResult

DEFAULT_RESUME_NAME = "LI Linghao-CV.pdf"


def build_prompts(resume_text: str) -> tuple[str, str]:
    system_prompt = (
        "You extract structured resume information for a career opportunity engine. "
        "Return only json."
    )
    user_prompt = (
        "Extract a structured candidate graph from this resume or academic CV. "
        "The document may be long, multi-section, bilingual, or contain publications. "
        "Focus on faithful extraction. Do not invent facts. "
        "Return concise but complete json with these fields: skills, summary, "
        "experience_highlights, constraints, evidence_spans, skill_evidence, "
        "experience_facts, education, projects, achievements, publications. "
        "For every major item, include evidence spans from the source text. "
        "Prefer sectioned evidence over paraphrase when possible.\n\n"
        "Resume text:\n"
        f"{resume_text}"
    )
    return system_prompt, user_prompt


def load_resume_text(resume_name: str) -> tuple[str, str]:
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                select file_name, parsed_text
                from resumes
                where file_name = :file_name
                order by created_at desc
                limit 1
                """
            ),
            {"file_name": resume_name},
        ).mappings().first()
    if row is None:
        raise RuntimeError(f"Resume not found: {resume_name}")
    return str(row["file_name"]), str(row["parsed_text"] or "")


def make_client() -> OpenAI:
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY is missing in .env")
    if not settings.llm_base_url:
        raise RuntimeError("LLM_BASE_URL is missing in .env")
    if not settings.llm_model:
        raise RuntimeError("LLM_MODEL is missing in .env")
    return OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=settings.llm_timeout_seconds,
    )


def run_non_streaming(client: OpenAI, system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
        max_tokens=settings.llm_max_output_tokens,
        extra_body={"enable_thinking": settings.llm_thinking},
    )
    content = response.choices[0].message.content or ""
    return content


def run_streaming(client: OpenAI, system_prompt: str, user_prompt: str) -> str:
    stream = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
        max_tokens=settings.llm_max_output_tokens,
        extra_body={"enable_thinking": settings.llm_thinking},
        stream=True,
    )
    chunks: list[str] = []
    for chunk in stream:
        try:
            delta = chunk.choices[0].delta.content or ""
        except Exception:
            delta = ""
        if delta:
            chunks.append(delta)
    return "".join(chunks)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe direct LLM resume parsing.")
    parser.add_argument("--resume-name", default=DEFAULT_RESUME_NAME)
    parser.add_argument("--stream", action="store_true")
    args = parser.parse_args()

    file_name, resume_text = load_resume_text(args.resume_name)
    if not resume_text.strip():
        raise RuntimeError(f"Resume text is empty: {file_name}")

    system_prompt, user_prompt = build_prompts(resume_text)
    client = make_client()

    print(f"provider={settings.llm_provider}")
    print(f"model={settings.llm_model}")
    print(f"base_url={settings.llm_base_url}")
    print(f"resume={file_name}")
    print(f"text_chars={len(resume_text)}")
    print(f"text_lines={len([line for line in resume_text.splitlines() if line.strip()])}")
    print(f"mode={'streaming' if args.stream else 'non_streaming'}")

    started = time.perf_counter()
    raw = (
        run_streaming(client, system_prompt, user_prompt)
        if args.stream
        else run_non_streaming(client, system_prompt, user_prompt)
    )
    elapsed = time.perf_counter() - started

    print(f"elapsed_seconds={elapsed:.2f}")
    print(f"raw_chars={len(raw)}")
    print(raw[:1200])

    parsed = parse_json_object(raw)
    validated = ResumeAnalysisResult.model_validate(parsed)
    print("validated=true")
    print(f"summary={validated.summary}")
    print(f"skills={json.dumps(validated.skills, ensure_ascii=False)}")
    print(f"education_count={len(validated.education)}")
    print(f"projects_count={len(validated.projects)}")
    print(f"achievements_count={len(validated.achievements)}")
    print(f"publications_count={len(validated.publications)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
