from app.llm.json_client import parse_json_object


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
