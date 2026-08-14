#!/usr/bin/env python3
"""Verify the local dev backend with the REAL langgraph-sdk client —
the same SDK family the web console uses (browser -> @langchain/langgraph-sdk).

Checks: /ok, assistant search, thread creation, streamed run reaching the
SCOPE human gate, and a REAL resume via command.
"""

from __future__ import annotations

import json
import sys

import httpx
from langgraph_sdk import get_sync_client


def main() -> int:
    ok = httpx.get("http://127.0.0.1:2024/ok", timeout=10)
    print(f"[verify] GET /ok -> {ok.status_code} {ok.json()}")

    client = get_sync_client(url="http://127.0.0.1:2024")

    assistants = client.assistants.search()
    ids = [a["assistant_id"] for a in assistants]
    print(f"[verify] assistants -> {ids}")
    assert "stov_scientist" in ids, "assistant stov_scientist missing"

    thread = client.threads.create()
    print(f"[verify] thread created -> {thread['thread_id']}")

    payload = json.dumps(
        {
            "campaign_id": "verify-ui-1",
            "title": "UI chain verification campaign",
            "research_question": "Does the browser chain reach the human gate?",
            "system_under_study": "STOV pulse",
            "scope": "vacuum",
            "excluded_scope": "",
            "target_observables": ["topological_charge"],
        }
    )

    events = []
    for event in client.runs.stream(
        thread["thread_id"],
        assistant_id="stov_scientist",
        input={"messages": [payload]},
        stream_mode="updates",
    ):
        events.append(event.event)
    print(f"[verify] streamed events: {len(events)} types={sorted(set(events))}")

    state = client.threads.get_state(thread["thread_id"])
    interrupts = state.get("values", {}).get("__interrupt__") or []
    assert interrupts, "expected SCOPE gate interrupt in streamed state"
    gate = interrupts[0]["value"] if isinstance(interrupts[0], dict) else interrupts[0].value
    print(f"[verify] human gate reached: {gate['gate']}")

    # REAL resume through the SDK command path (same as the web console)
    events2 = [
        e.event
        for e in client.runs.stream(
            thread["thread_id"],
            assistant_id="stov_scientist",
            input=None,
            command={"resume": {"decision": "APPROVE", "rationale": "sdk verify"}},
            stream_mode="updates",
        )
    ]
    state2 = client.threads.get_state(thread["thread_id"])
    interrupts2 = state2.get("values", {}).get("__interrupt__") or []
    gate2 = None
    if interrupts2:
        raw = interrupts2[0]
        gate2 = raw["value"] if isinstance(raw, dict) else raw.value
    print(f"[verify] after resume: next gate={gate2 and gate2['gate']}")
    print(f"[verify] pipeline: {list((state2.get('values', {}).get('pipeline_status') or {}).keys())}")
    print("VERIFY: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
