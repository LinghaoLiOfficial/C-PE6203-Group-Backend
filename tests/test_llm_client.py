from types import SimpleNamespace

import pytest

from app.core import config as config_module
from app.llm import client as client_module
from app.llm.client import LLMResponseFormatError, OpenAICompatibleLLMClient


def _reload_client_settings(monkeypatch) -> None:
    config_module.get_settings.cache_clear()
    config_module.settings = config_module.get_settings()
    monkeypatch.setattr(client_module, "settings", config_module.settings)


def test_groq_provider_uses_groq_defaults(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("LLM_BASE_URL", "")
    _reload_client_settings(monkeypatch)

    client = OpenAICompatibleLLMClient()

    assert client.provider == "groq"
    assert client.metadata.request_url == "https://api.groq.com/openai/v1/chat/completions"
    assert config_module.settings.llm_configured is True


def test_build_request_body_disables_thinking_and_sets_output_limit(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_THINKING", "false")
    monkeypatch.setenv("LLM_MAX_OUTPUT_TOKENS", "4096")
    _reload_client_settings(monkeypatch)

    client = OpenAICompatibleLLMClient()
    body = client._build_request_body("Return json.", "resume", None)

    assert body["max_tokens"] == 4096
    assert body["extra_body"] == {"enable_thinking": False}
    assert body["response_format"] == {"type": "json_object"}


def test_invoke_rejects_truncated_json(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    _reload_client_settings(monkeypatch)

    client = OpenAICompatibleLLMClient()
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content='{"summary":"partial'),
                finish_reason="length",
            )
        ]
    )
    monkeypatch.setattr(client, "_create_chat_completion", lambda *_args, **_kwargs: response)

    with pytest.raises(LLMResponseFormatError, match="truncated"):
        client.invoke("Return json.", "resume")
