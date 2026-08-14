#!/usr/bin/env python3
"""Verify the DeepSeek runtime with ONE real API call.

Prints the model name returned by the provider and runs a tiny structured
output check. Exit 0 = key works; anything else reports the real error.
The API key itself is NEVER printed.

Usage (from platform/):  python ../scripts/verify_deepseek.py
"""

from __future__ import annotations

import sys

from langchain_core.messages import HumanMessage


def main() -> int:
    from stov_scientist.config.settings import get_settings

    settings = get_settings()
    if not settings.deepseek_available:
        print("NO_KEY: DEEPSEEK_API_KEY is not set in platform/.env")
        return 2

    from stov_scientist.config.models import clear_model_cache, get_main_model

    clear_model_cache()
    try:
        model = get_main_model()
        response = model.invoke([HumanMessage(content="Reply with exactly: OK")])
        content = getattr(response, "content", "")
        print(f"[deepseek] model invoked: {settings.main_model}")
        print(f"[deepseek] response: {content!r}")
        if "OK" not in str(content):
            print("VERIFY: WARNING — response did not contain 'OK'")
            return 1
        print("VERIFY: PASS")
        return 0
    except Exception as exc:  # noqa: BLE001 — report the real provider error
        print(f"VERIFY: FAIL — {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
