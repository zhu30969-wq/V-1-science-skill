"""DeepSeek model factory (spec PHASE 2 §6).

Uniform access points:

    get_main_model()  -> deepseek-v4-pro  (reasoning, hypothesis, mechanism,
                                           counterexample, synthesis)
    get_fast_model()  -> deepseek-v4-flash (metadata, classification,
                                           normalization, routine extraction)

Model names, timeout, retry, temperature and streaming all come from
``Settings``. No agent module may instantiate ``ChatDeepSeek`` directly.

NOTE: the Claude Code development environment may itself connect via
ANTHROPIC_*; that is irrelevant here — the STOV runtime only ever uses
DEEPSEEK_API_KEY.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_deepseek import ChatDeepSeek

from stov_scientist.config.settings import get_settings
from stov_scientist.errors import ConfigurationError


def _require_api_key():
    settings = get_settings()
    if not settings.deepseek_available:
        raise ConfigurationError(
            "DEEPSEEK_API_KEY is not configured. Set it in platform/.env "
            "(see platform/.env.example). The rest of the platform remains "
            "fully testable without it via the deterministic fake model."
        )
    return settings.deepseek_api_key


class _ExtraBodyCompletions:
    """Wraps chat.completions to inject ``extra_body`` parameters.

    The DeepSeek v4 model family defaults to THINKING MODE, which rejects
    tool_choice (the structured-output mechanism). Disabling thinking
    requires the body field ``thinking={"type": "disabled"}`` — the OpenAI
    client only accepts unknown fields through ``extra_body``.
    """

    def __init__(self, inner, extra_body: dict) -> None:
        self._inner = inner
        self._extra_body = extra_body

    def __getattr__(self, name: str):
        return getattr(self._inner, name)

    def _merge(self, kwargs: dict) -> dict:
        kwargs["extra_body"] = {**self._extra_body, **(kwargs.get("extra_body") or {})}
        return kwargs

    def create(self, **kwargs):
        return self._inner.create(**self._merge(kwargs))

    async def acreate(self, **kwargs):
        return await self._inner.acreate(**self._merge(kwargs))


def _build(model_name: str) -> ChatDeepSeek:
    settings = get_settings()
    model = ChatDeepSeek(
        model=model_name,
        api_key=_require_api_key(),
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
        temperature=settings.llm_temperature,
        streaming=settings.llm_streaming,
    )
    if settings.llm_thinking == "disabled" and model.root_client is not None:
        extra = {"thinking": {"type": "disabled"}}
        model.client = _ExtraBodyCompletions(model.root_client.chat.completions, extra)
        if model.root_async_client is not None:
            model.async_client = _ExtraBodyCompletions(
                model.root_async_client.chat.completions, extra
            )
    return model


@lru_cache(maxsize=1)
def get_main_model() -> ChatDeepSeek:
    """Complex reasoning model: hypothesis, mechanism, counterexample, synthesis."""
    return _build(get_settings().main_model)


@lru_cache(maxsize=1)
def get_fast_model() -> ChatDeepSeek:
    """Fast model: metadata, classification, normalization, routine extraction."""
    return _build(get_settings().fast_model)


def clear_model_cache() -> None:
    """Test helper: drop cached model instances."""
    get_main_model.cache_clear()
    get_fast_model.cache_clear()
