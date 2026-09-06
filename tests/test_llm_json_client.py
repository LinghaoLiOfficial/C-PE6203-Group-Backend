from app.llm.json_client import parse_json_object
from app.schemas.ai import ResumeAnalysisResult


def test_parse_json_object_strips_think_wrapper() -> None:
    raw = """
    <think>planning the schema</think>
    {
      "skills": ["Python", "FastAPI"],
      "summary": "Backend engineer",
      "experience_highlights": ["Built APIs"]
    }
    """

    payload = parse_json_object(raw)

    assert payload["skills"] == ["Python", "FastAPI"]
    assert payload["summary"] == "Backend engineer"
    assert payload["experience_highlights"] == ["Built APIs"]


def test_resume_analysis_accepts_common_llm_collection_shapes() -> None:
    result = ResumeAnalysisResult.model_validate(
        {
            "skills": [{"name": "Python", "proficiency": "Advanced"}],
            "experience_highlights": [{"role": "Analyst", "description": "Built models"}],
            "evidence_spans": ["GPA: 3.78 / 4.00"],
            "skill_evidence": {"Python": ["Used Python in projects"]},
        }
    )

    assert result.skills == ["Python"]
    assert result.experience_highlights == ["Analyst: Built models"]
    assert result.evidence_spans[0].text == "GPA: 3.78 / 4.00"
    assert result.skill_evidence[0].evidence[0].text == "Used Python in projects"
