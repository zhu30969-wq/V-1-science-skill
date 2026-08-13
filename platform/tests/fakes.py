"""Deterministic fake chat model for LangGraph unit tests (spec §71).

The fake returns scripted JSON payloads. It supports the structured-output
contract used by the workers (with_structured_output) and lets tests script
a first invalid response + retry (STRUCTURED_OUTPUT_FAILURE paths).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class FakeChatModel(BaseChatModel):
    """Scripted responses: (trigger_substring, payload) pairs.

    The first payload matching the last message content wins; payloads may
    be dicts (JSON) or raise instructions ("_raise": "Message").
    """

    responses: list[tuple[str, Any]] = Field(default_factory=list)
    calls: list[str] = Field(default_factory=list)

    def __init__(self, responses: list[tuple[str, Any]] | None = None, **kwargs: Any) -> None:
        super().__init__(responses=responses or [], **kwargs)
        self.calls = []

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        last = str(messages[-1].content)
        self.calls.append(last[:200])
        for trigger, payload in self.responses:
            if trigger in last:
                if isinstance(payload, dict) and payload.get("_raise"):
                    raise RuntimeError(payload["_raise"])
                text = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
                return ChatResult(
                    generations=[ChatGeneration(message=AIMessage(content=text))]
                )
        # default: empty JSON object
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="{}"))])

    @property
    def _llm_type(self) -> str:
        return "fake-chat-model"

    def with_structured_output(self, schema: type, **kwargs: Any) -> Any:
        return _FakeStructuredOutput(self, schema)


class _FakeStructuredOutput:
    def __init__(self, model: FakeChatModel, schema: type) -> None:
        self.model = model
        self.schema = schema

    def invoke(self, messages: Sequence[BaseMessage]) -> Any:
        result = self.model._generate(list(messages))
        content = result.generations[0].message.content
        payload = json.loads(str(content))
        return self.schema.model_validate(payload)


def scripted_model(
    *pairs: tuple[str, Any],
) -> FakeChatModel:
    return FakeChatModel(list(pairs))
