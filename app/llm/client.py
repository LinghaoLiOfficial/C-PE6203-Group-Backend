from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx
import openai
from groq import Groq

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_TEMPERATURE = 0.2
DEFAULT_RESPONSE_FORMAT = {"type": "json_object"}
REQUEST_ERROR_DETAIL = (
    "LLM request failed. Please check the model service URL, model name, API key,"
    " or provider response."
)
RESPONSE_FORMAT_ERROR_DETAIL = (
    "The structured response from the LLM is invalid. Please retry or adjust the"
    " model configuration."
)
EMPTY_RESPONSE_DETAIL = "The LLM returned an empty response and cannot produce structured output."
CONFIGURATION_ERROR_DETAIL = (
    "The LLM service is not configured. Please check LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL."
)


class LLMConfigurationError(RuntimeError):
    """Raised when required LLM settings are missing."""


class LLMRequestError(RuntimeError):
    """Raised when the LLM provider request fails."""


class LLMResponseFormatError(RuntimeError):
    """Raised when the LLM provider returns an unusable response."""


class LLMEmptyResponseError(LLMResponseFormatError):
    """Raised when the LLM response content is empty."""


@dataclass(frozen=True)
class LLMRequestMetadata:
    provider: str
    base_url: str
    request_url: str
    model: str
    timeout: float
    stream_read_timeout: float
    use_response_format: bool
    has_api_key: bool


class OpenAICompatibleLLMClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        stream_read_timeout: float | None = None,
        provider: str | None = None,
        use_response_format: bool | None = None,
    ) -> None:
        resolved_provider = provider if provider is not None else settings.llm_provider
        self.provider = resolved_provider.strip().lower()
        configured_base_url = base_url if base_url is not None else settings.llm_base_url
        self.base_url = (configured_base_url or "").strip()
        self.api_key = ((api_key if api_key is not None else settings.llm_api_key) or "").strip()
        self.model = ((model if model is not None else settings.llm_model) or "").strip()
        self.timeout = timeout if timeout is not None else settings.llm_timeout_seconds
        self.stream_read_timeout = (
            stream_read_timeout
            if stream_read_timeout is not None
            else settings.llm_stream_read_timeout_seconds
        )
        self.use_response_format = (
            use_response_format
            if use_response_format is not None
            else settings.llm_use_response_format
        )

    @property
    def metadata(self) -> LLMRequestMetadata:
        return LLMRequestMetadata(
            provider=self.provider,
            base_url=self.base_url,
            request_url=self._request_url(),
            model=self.model,
            timeout=self.timeout,
            stream_read_timeout=self.stream_read_timeout,
            use_response_format=self.use_response_format,
            has_api_key=bool(self.api_key),
        )

    def invoke(
        self,
        system_prompt: str,
        user_payload: dict[str, Any] | str,
        extra_params: dict[str, Any] | None = None,
    ) -> str:
        self._validate_configuration()
        request_body = self._build_request_body(system_prompt, user_payload, extra_params)
        logger.info(
            "llm.request.start provider=%s base_url=%s model=%s timeout=%s use_response_format=%s",
            self.provider,
            self.base_url,
            self.model,
            self.timeout,
            self.use_response_format,
        )
        try:
            response = self._create_chat_completion(request_body, stream=False)
        except Exception as exc:
            self._raise_request_error(exc)
        content = extract_chat_completion_content(response)
        logger.info(
            "llm.request.success provider=%s content_length=%s",
            self.provider,
            len(content),
        )
        return content

    def stream(
        self,
        system_prompt: str,
        user_payload: dict[str, Any] | str,
        extra_params: dict[str, Any] | None = None,
    ) -> Iterator[str]:
        self._validate_configuration()
        request_body = self._build_request_body(system_prompt, user_payload, extra_params)
        logger.info(
            "llm.stream.start provider=%s base_url=%s model=%s timeout=%s "
            "stream_read_timeout=%s use_response_format=%s",
            self.provider,
            self.base_url,
            self.model,
            self.timeout,
            self.stream_read_timeout,
            self.use_response_format,
        )
        try:
            stream = self._create_chat_completion(request_body, stream=True)
            for chunk in stream:
                delta = self._extract_stream_delta(chunk)
                if delta is None:
                    continue
                yield delta
        except LLMRequestError:
            raise
        except Exception as exc:
            self._raise_request_error(exc)
        logger.info("llm.stream.success provider=%s model=%s", self.provider, self.model)

    def _request_url(self) -> str:
        if self.provider == "groq":
            return "https://api.groq.com/openai/v1/chat/completions"
        return build_chat_completions_url(self.base_url)

    def _create_chat_completion(self, request_body: dict[str, Any], *, stream: bool) -> Any:
        if self.provider == "groq":
            client = Groq(api_key=self.api_key)
            return client.chat.completions.create(
                **request_body,
                stream=stream,
            )

        client = openai.OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        )
        return client.chat.completions.create(
            **request_body,
            stream=stream,
        )

    def _extract_stream_delta(self, chunk: Any) -> str | None:
        if self.provider == "groq":
            try:
                choices = getattr(chunk, "choices", None)
                if not choices:
                    return None
                first_choice = choices[0]
                delta = getattr(first_choice, "delta", None)
                if delta is None:
                    return None
                content = getattr(delta, "content", None)
                if content is None:
                    return None
                if not isinstance(content, str):
                    raise LLMResponseFormatError("LLM stream delta content must be a string.")
                return content
            except LLMResponseFormatError:
                raise
            except Exception as exc:
                raise LLMResponseFormatError("LLM stream chunk is invalid.") from exc
        return extract_chat_completion_stream_delta(chunk)

    def _raise_request_error(self, exc: Exception) -> None:
        if isinstance(exc, httpx.HTTPError):
            logger.warning(
                "llm.request.failed provider=%s error_type=%s message=%s",
                self.provider,
                type(exc).__name__,
                _excerpt(str(exc), 500),
            )
            raise LLMRequestError("LLM API request failed before receiving a response.") from exc
        logger.warning(
            "llm.request.failed provider=%s error_type=%s message=%s",
            self.provider,
            type(exc).__name__,
            _excerpt(str(exc), 500),
        )
        raise LLMRequestError("LLM API request failed.") from exc

    def _validate_configuration(self) -> None:
        missing = []
        if not self.api_key:
            missing.append("LLM_API_KEY")
        if self.provider != "groq" and not self.base_url:
            missing.append("LLM_BASE_URL")
        if not self.model:
            missing.append("LLM_MODEL")
        if missing:
            logger.warning(
                "llm.configuration.missing provider=%s base_url=%s model=%s "
                "has_api_key=%s missing=%s",
                self.provider,
                self.base_url,
                self.model,
                bool(self.api_key),
                ",".join(missing),
            )
            raise LLMConfigurationError(f"Missing LLM configuration: {', '.join(missing)}.")

    def _build_request_body(
        self,
        system_prompt: str,
        user_payload: dict[str, Any] | str,
        extra_params: dict[str, Any] | None,
    ) -> dict[str, Any]:
        user_content = (
            user_payload
            if isinstance(user_payload, str)
            else json.dumps(user_payload, ensure_ascii=False, indent=2)
        )
        request_body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": DEFAULT_TEMPERATURE,
        }
        if self.use_response_format:
            request_body["response_format"] = DEFAULT_RESPONSE_FORMAT
        if extra_params:
            request_body.update(extra_params)
        return request_body


def build_chat_completions_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        return "/chat/completions"
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def extract_chat_completion_content(response: Any) -> str:
    try:
        choices = response.choices
    except AttributeError as exc:
        logger.warning("llm.response.invalid reason=missing_choices")
        raise LLMResponseFormatError("LLM response missing choices.") from exc
    if not choices:
        logger.warning("llm.response.invalid reason=empty_choices")
        raise LLMResponseFormatError("LLM response choices is empty.")
    try:
        content = choices[0].message.content
    except AttributeError as exc:
        logger.warning("llm.response.invalid reason=missing_message_content")
        raise LLMResponseFormatError("LLM response missing message content.") from exc
    if not isinstance(content, str) or not content.strip():
        logger.warning("llm.response.invalid reason=empty_content")
        raise LLMEmptyResponseError("LLM response content is empty.")
    return content


def extract_chat_completion_stream_delta(line: str | bytes) -> str | None:
    if isinstance(line, bytes):
        line = line.decode("utf-8", errors="replace")
    line = line.strip()
    if not line or line.startswith(":"):
        return None
    if not line.startswith("data:"):
        return None

    data = line.removeprefix("data:").strip()
    if not data or data == "[DONE]":
        return None
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        logger.warning(
            "llm.stream.invalid reason=invalid_json line_excerpt=%s",
            _excerpt(data, 1000),
        )
        return None

    if isinstance(payload, dict) and payload.get("error") is not None:
        logger.warning("llm.stream.invalid reason=provider_error")
        raise LLMRequestError("LLM stream returned an error chunk.")
    if not isinstance(payload, dict):
        logger.warning("llm.stream.invalid reason=payload_not_object")
        raise LLMResponseFormatError("LLM stream chunk must be a JSON object.")

    choices = payload.get("choices")
    if choices is None:
        return None
    if not isinstance(choices, list):
        logger.warning("llm.stream.invalid reason=choices_not_list")
        raise LLMResponseFormatError("LLM stream chunk choices must be a list.")
    if not choices:
        return None

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        logger.warning("llm.stream.invalid reason=choice_not_object")
        raise LLMResponseFormatError("LLM stream choice must be an object.")

    delta = first_choice.get("delta")
    if isinstance(delta, dict):
        content = delta.get("content")
        if content is None:
            return None
        if not isinstance(content, str):
            logger.warning("llm.stream.invalid reason=delta_content_not_string")
            raise LLMResponseFormatError("LLM stream delta content must be a string.")
        return content

    message = first_choice.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if content is None:
            return None
        if not isinstance(content, str):
            logger.warning("llm.stream.invalid reason=message_content_not_string")
            raise LLMResponseFormatError("LLM stream message content must be a string.")
        return content

    text = first_choice.get("text")
    if text is None:
        return None
    if not isinstance(text, str):
        logger.warning("llm.stream.invalid reason=text_not_string")
        raise LLMResponseFormatError("LLM stream text must be a string.")
    return text


def _mentions_response_format(text: str) -> bool:
    lowered = text.lower()
    return "response_format" in lowered or "json_object" in lowered


def _excerpt(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."
