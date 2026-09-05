from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.llm.client import (
    DEFAULT_TEMPERATURE,
    LLMConfigurationError,
    LLMEmptyResponseError,
    LLMRequestError,
    LLMResponseFormatError,
    OpenAICompatibleLLMClient,
)
from app.llm.json_client import parse_json_object
from app.services.llm_generation_runtime import (
    LLMPartialStreamError,
    collect_llm_stream_text,
)

logger = logging.getLogger(__name__)

LLMClientFactory = Callable[[], OpenAICompatibleLLMClient]


def generate_structured_json(
    system_prompt: str,
    user_payload: dict[str, Any] | str,
    *,
    response_model: type[BaseModel],
    llm_client_factory: LLMClientFactory | None = None,
    max_retries: int | None = None,
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if llm_client_factory is not None or not settings.llm_configured:
        return _generate_structured_json_from_stream(
            system_prompt,
            user_payload,
            response_model=response_model,
            llm_client_factory=llm_client_factory or OpenAICompatibleLLMClient,
            extra_params=extra_params,
        )
    return _generate_structured_json_with_instructor(
        system_prompt,
        user_payload,
        response_model=response_model,
        max_retries=max_retries,
    )


def _generate_structured_json_with_instructor(
    system_prompt: str,
    user_payload: dict[str, Any] | str,
    *,
    response_model: type[BaseModel],
    max_retries: int | None,
) -> dict[str, Any]:
    _validate_configuration()
    retries = settings.llm_structured_max_retries if max_retries is None else max_retries
    client = OpenAICompatibleLLMClient()
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            extra_params: dict[str, Any] = {"temperature": DEFAULT_TEMPERATURE}
            if settings.llm_use_response_format:
                extra_params["response_format"] = {"type": "json_object"}
            raw = client.invoke(
                system_prompt,
                user_payload,
                extra_params=extra_params,
            )
            if not isinstance(raw, str) or not raw.strip():
                raise LLMEmptyResponseError("LLM structured response is empty.")
            payload = parse_json_object(raw)
            return response_model.model_validate(payload).model_dump(mode="json")
        except LLMRequestError as exc:
            last_error = exc
            if attempt >= retries:
                break
        except (ValidationError, LLMResponseFormatError) as exc:
            last_error = exc
            if attempt >= retries:
                break
    if isinstance(last_error, ValidationError):
        logger.warning(
            "llm.structured.validation_failed response_model=%s error=%s",
            response_model.__name__,
            _excerpt(str(last_error), 500),
        )
    elif last_error is not None:
        logger.warning(
            "llm.structured.retry_exhausted response_model=%s message=%s",
            response_model.__name__,
            _excerpt(str(last_error), 500),
        )
    raise LLMResponseFormatError(
        f"LLM structured output failed schema validation: {response_model.__name__}."
    )


def _generate_structured_json_from_stream(
    system_prompt: str,
    user_payload: dict[str, Any] | str,
    *,
    response_model: type[BaseModel],
    llm_client_factory: LLMClientFactory,
    extra_params: dict[str, Any] | None,
) -> dict[str, Any]:
    partial_error: LLMPartialStreamError | None = None
    try:
        raw = collect_llm_stream_text(
            system_prompt,
            user_payload,
            llm_client_factory=llm_client_factory,
            extra_params=extra_params,
        )
    except LLMPartialStreamError as exc:
        partial_error = exc
        raw = exc.partial_text
    try:
        parsed = parse_json_object(raw)
    except LLMResponseFormatError as exc:
        if partial_error is not None:
            raise partial_error from exc
        raise
    try:
        return response_model.model_validate(parsed).model_dump(mode="json")
    except ValidationError as exc:
        logger.warning(
            "llm.structured.stream_validation_failed response_model=%s error=%s",
            response_model.__name__,
            _excerpt(str(exc), 500),
        )
        raise LLMResponseFormatError(
            f"LLM structured output failed schema validation: {response_model.__name__}."
        ) from exc


def _validate_configuration() -> None:
    missing = []
    if not settings.llm_api_key:
        missing.append("LLM_API_KEY")
    if settings.llm_provider.lower() != "groq" and not settings.llm_base_url:
        missing.append("LLM_BASE_URL")
    if not settings.llm_model:
        missing.append("LLM_MODEL")
    if missing:
        raise LLMConfigurationError(f"Missing LLM configuration: {', '.join(missing)}.")


def _excerpt(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."


__all__ = ["generate_structured_json"]
