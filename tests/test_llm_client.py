from app.llm.client import OpenAICompatibleLLMClient


def test_groq_provider_uses_groq_defaults(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("LLM_BASE_URL", "")

    from app.core import config as config_module

    config_module.get_settings.cache_clear()
    config_module.settings = config_module.get_settings()

    client = OpenAICompatibleLLMClient()

    assert client.provider == "groq"
    assert client.metadata.request_url == "https://api.groq.com/openai/v1/chat/completions"
    assert config_module.settings.llm_configured is True

    config_module.get_settings.cache_clear()
    config_module.settings = config_module.get_settings()
