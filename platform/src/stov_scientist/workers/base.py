"""Bounded research workers (spec PHASE 8, §32-§34).

Deep Agents are long-horizon bounded workers; LangGraph remains the
Scientific Control Plane and decides when to call which worker.

Skill isolation (spec §33): each worker declares its own skill set — the
full skill library is never injected into every agent.

Structured output (spec §34): worker output must land in Pydantic schemas.
Failure -> one retry -> STRUCTURED_OUTPUT_FAILURE. No infinite retries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeVar

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from stov_scientist.config.settings import get_settings
from stov_scientist.errors import StructuredOutputFailure

T = TypeVar("T", bound=BaseModel)


@dataclass
class WorkerResult:
    status: str  # OK / STRUCTURED_OUTPUT_FAILURE / WORKER_ERROR
    value: Any | None = None
    error: str = ""
    attempts: int = 0

    @property
    def ok(self) -> bool:
        return self.status == "OK"


@dataclass
class WorkerConfig:
    """Bounded worker configuration (skill isolation per spec §33)."""

    worker_id: str
    description: str
    skills: list[str] = field(default_factory=list)
    tools: list[Any] = field(default_factory=list)
    model_kind: str = "main"  # main | fast
    max_iterations: int = 12


def structured_llm(model: BaseChatModel, schema: type[T]) -> Any:
    """Best-effort structured output binding (function-calling based).

    DeepSeek exposes JSON-schema function calling through langchain-deepseek;
    this is the Deep Agents structured-response mechanism per spec §34.
    """
    try:
        return model.with_structured_output(schema)
    except Exception as exc:
        return _ManualStructuredLLM(model, schema, str(exc))


class _ManualStructuredLLM:
    """Fallback: ask for JSON, then validate with Pydantic."""

    def __init__(self, model: BaseChatModel, schema: type[T], reason: str) -> None:
        self.model = model
        self.schema = schema
        self.reason = reason

    def invoke(self, messages: list[BaseMessage]) -> Any:
        import json

        response = self.model.invoke(messages)
        text = getattr(response, "content", "")
        if isinstance(text, list):
            text = "".join(str(part) for part in text)
        try:
            payload = json.loads(str(text))
        except json.JSONDecodeError as exc:
            raise StructuredOutputFailure(f"non-JSON structured output: {exc}") from exc
        try:
            return self.schema.model_validate(payload)
        except PydanticValidationError as exc:
            raise StructuredOutputFailure(f"schema validation failed: {exc}") from exc


def run_structured(
    model: BaseChatModel,
    schema: type[T],
    messages: list[BaseMessage],
) -> WorkerResult:
    """Run a structured-output worker call with exactly one retry."""
    max_retries = get_settings().structured_output_max_retries
    bound = structured_llm(model, schema)
    last_error = ""
    for attempt in range(max_retries + 1):
        try:
            value = bound.invoke(messages)
            # re-validate: with_structured_output can still return raw text
            if not isinstance(value, schema):
                value = schema.model_validate(value)
            return WorkerResult(status="OK", value=value, attempts=attempt + 1)
        except StructuredOutputFailure as exc:
            last_error = str(exc)
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < max_retries:
            messages = [
                *messages,
                _retry_nudge(
                    f"Your previous output was invalid: {last_error}. "
                    "Return ONLY valid JSON matching the requested schema."
                ),
            ]
    return WorkerResult(
        status="STRUCTURED_OUTPUT_FAILURE",
        error=last_error,
        attempts=max_retries + 1,
    )


def _retry_nudge(text: str) -> BaseMessage:
    from langchain_core.messages import HumanMessage

    return HumanMessage(content=text)


def make_deep_agent(
    tools: list[Any],
    system_prompt: str,
    *,
    model: BaseChatModel,
    max_iterations: int = 12,
) -> Any:
    """Build a bounded agent: deepagents.create_deep_agent when available,
    else langgraph.prebuilt.create_agent (same bounded-worker contract)."""
    try:
        from deepagents import create_deep_agent

        return create_deep_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
        )
    except ImportError:
        from langgraph.prebuilt import create_react_agent

        return create_react_agent(
            model=model,
            tools=tools,
            prompt=system_prompt,
        )
    except TypeError:
        from langgraph.prebuilt import create_react_agent

        return create_react_agent(
            model=model,
            tools=tools,
            prompt=system_prompt,
        )
