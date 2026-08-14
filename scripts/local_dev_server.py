#!/usr/bin/env python3
"""LOCAL DEV SERVER — stdlib-only adapter exposing the minimal LangGraph
assistant HTTP API for the web console.

WHY THIS EXISTS: the official `langgraph dev` server requires
`langgraph-cli[inmem]`, whose langgraph-api conflicts with langserve
(pulled by deepagents) in the same environment. This adapter runs the REAL
ResearchGraph (graph_with_memory, InMemorySaver — dev-only per spec §51)
with REAL interrupts and REAL Command(resume=...). No state is faked.

This is a development shim, NOT a second production runtime: production
deploys use the official LangGraph platform (spec ADR-010).

Usage (from platform/):
    uv run python ../scripts/local_dev_server.py --port 2024
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from stov_scientist.artifacts.local_store import LocalStore
from stov_scientist.artifacts.registry import ArtifactRegistry
from stov_scientist.campaign.manager import CampaignManager
from stov_scientist.control.research_graph import graph_with_memory
from stov_scientist.control.services import ServiceBundle
from stov_scientist.evidence.claims import ClaimLedger
from stov_scientist.evidence.ledger import EvidenceLedger
from stov_scientist.simulation import SimulationRunner, default_solver_registry

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSISTANT_ID = "stov_scientist"
RUN_ID = f"run-{uuid.uuid4().hex[:12]}"

# thread_id -> services (one ServiceBundle per campaign thread)
THREAD_SERVICES: dict[str, ServiceBundle] = {}
THREAD_STATE: dict[str, dict] = {}
LOCK = threading.Lock()

# The compiled graph MUST be a singleton: InMemorySaver holds the
# checkpoints; building a new graph per request would lose the thread
# checkpoints and break resume.
_GRAPH: object | None = None


def _graph() -> object:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = graph_with_memory(None)
    return _GRAPH


def _services_for(thread_id: str) -> ServiceBundle:
    with LOCK:
        services = THREAD_SERVICES.get(thread_id)
        if services is None:
            from stov_scientist.config.settings import get_settings
            from stov_scientist.control.services import LazyModel

            settings = get_settings()
            # Real DeepSeek models when DEEPSEEK_API_KEY is present in
            # platform/.env; LazyModel defers construction until first use,
            # and graph nodes degrade to deterministic fallbacks on any
            # provider error (never crashes the pipeline).
            main_model = LazyModel("main") if settings.deepseek_available else None
            fast_model = LazyModel("fast") if settings.deepseek_available else None
            artifacts = ArtifactRegistry(
                LocalStore(REPO_ROOT / "artifacts"), workdir=REPO_ROOT
            )
            services = ServiceBundle(
                main_model=main_model,
                fast_model=fast_model,
                simulation=SimulationRunner(default_solver_registry(), artifacts),
                artifacts=artifacts,
                evidence=EvidenceLedger(),
                claims=ClaimLedger(),
                campaigns=CampaignManager(REPO_ROOT / "campaigns", workdir=REPO_ROOT),
                workdir=REPO_ROOT,
                extra={"literature_clients": {}},
            )
            THREAD_SERVICES[thread_id] = services
        return services


def _emit(wfile, event: str, data: dict) -> None:
    payload = json.dumps(data, default=str, ensure_ascii=False)
    frame = f"event: {event}\ndata: {payload}\n\n".encode("utf-8")
    wfile.write(frame)
    wfile.flush()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "stov-local-dev/0.1"

    # -- plumbing ----------------------------------------------------------
    def log_message(self, *args: object) -> None:
        sys.stderr.write(f"[stov-dev] {args[0] % args[1:]}\n")

    def _read_json(self) -> dict:
        length = int(self.headers.get("content-length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _cors(self) -> None:
        # must be called AFTER send_response() — headers before the status
        # line are a protocol violation.
        # The gateway enforces the real CORS policy; this local shim is
        # reached through the gateway in the web flow.
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-headers", "content-type,x-api-key")
        self.send_header("access-control-allow-methods", "GET,POST,OPTIONS")

    def _send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, default=str, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_sse(self) -> None:
        self.send_response(200)
        self._cors()
        self.send_header("content-type", "text/event-stream")
        self.send_header("cache-control", "no-cache")
        self.send_header("connection", "keep-alive")
        self.end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    # -- LangGraph assistant API (minimal surface used by the SDK) ---------
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/ok":
            self._send_json({"ok": True})
            return
        if path == "/info":
            self._send_json({"version": "0.1.0", "langgraph_api_version": "local-dev-shim"})
            return
        parts = [p for p in path.split("/") if p]
        if len(parts) == 3 and parts[0] == "threads" and parts[2] == "state":
            thread_id = parts[1]
            snapshot = THREAD_STATE.get(thread_id, {})
            self._send_json(
                {
                    "values": snapshot,
                    "next": [],
                    "checkpoint": {"thread_id": thread_id},
                }
            )
            return
        self._send_json({"error": "not_found", "detail": path}, 404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self._read_json()

        if path == "/assistants/search":
            self._send_json(
                [
                    {
                        "assistant_id": ASSISTANT_ID,
                        "graph_id": ASSISTANT_ID,
                        "config": {},
                        "metadata": {"created_by": "local-dev"},
                    }
                ]
            )
            return

        if path == "/threads":
            thread_id = str(uuid.uuid4())
            THREAD_STATE[thread_id] = {}
            self._send_json(
                {
                    "thread_id": thread_id,
                    "created_at": "2026-08-13T00:00:00Z",
                    "status": "idle",
                    "metadata": {},
                    "values": {},
                },
                201,
            )
            return

        parts = [p for p in path.split("/") if p]
        if len(parts) >= 3 and parts[0] == "threads":
            thread_id = parts[1]
            endpoint = parts[2]
            if endpoint in ("runs", "runs/stream"):
                self._handle_run(thread_id, body)
                return
        self._send_json({"error": "not_found", "detail": path}, 404)

    def _handle_run(self, thread_id: str, body: dict) -> None:
        self._send_sse()
        # SSE over HTTP/1.1: close the connection when the stream ends so
        # SDK clients see EOF (no content-length on event streams)
        self.close_connection = True
        wfile = self.wfile
        graph = _graph()
        services = _services_for(thread_id)
        config = {"configurable": {"services": services, "thread_id": thread_id}}

        try:
            _emit(wfile, "metadata", {"run_id": RUN_ID, "attempt": 1})

            command = body.get("command")
            if command is not None:
                resume = command.get("resume")
                stream = graph.stream(Command(resume=resume), config=config, stream_mode="updates")
            else:
                raw_input = body.get("input") or {}
                messages = raw_input.get("messages") or []
                if isinstance(messages, str):
                    messages = [messages]
                content = messages[-1] if messages else ""
                stream = graph.stream(
                    {"messages": [HumanMessage(content=str(content))]},
                    config=config,
                    stream_mode="updates",
                )

            for chunk in stream:
                _emit(wfile, "values", chunk)

            # final state snapshot; LangGraph 1.2 stores interrupts in the
            # checkpoint tasks, not in values — surface them explicitly so
            # the SDK (browser + python) sees the human-gate payload
            snapshot = graph.get_state(config)
            values = dict(snapshot.values) if snapshot.values else {}
            interrupts = []
            for task in snapshot.tasks or []:
                for intr in task.interrupts or []:
                    interrupts.append({"value": intr.value})
            if interrupts:
                values["__interrupt__"] = interrupts
            THREAD_STATE[thread_id] = values
            _emit(wfile, "values", values)
            _emit(wfile, "end", {})
        except Exception as exc:  # noqa: BLE001 — surface as stream error frame
            _emit(wfile, "error", {"message": f"{type(exc).__name__}: {exc}"})
            _emit(wfile, "end", {})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=2024)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"[stov-local-dev] serving LangGraph assistant API on "
          f"http://127.0.0.1:{args.port} (dev shim, InMemorySaver)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
