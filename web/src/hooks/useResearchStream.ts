"use client";

/**
 * Graph streaming hook (spec §56, §57). State MUST come from the real
 * LangGraph stream: values from `useStream`; the Human Gate renders the
 * active `interrupt.value`; resume sends a real Command via
 * `submit(null, { command: { resume } })` — never frontend fake state.
 */

import { useCallback, useMemo } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import type { GateDecision, GatePayload, ResearchState } from "@/lib/types";
import { ASSISTANT_ID, GATEWAY_URL } from "@/lib/api";

type InterruptLike = { value?: unknown } | unknown;

export function useResearchStream() {
  const stream = useStream<ResearchState>({
    apiUrl: GATEWAY_URL,
    assistantId: ASSISTANT_ID,
  });

  const start = useCallback(
    (question: string, extra: Record<string, unknown> = {}) => {
      stream.submit(
        { messages: [JSON.stringify({ research_question: question, ...extra })] },
        { config: { configurable: {} } }
      );
    },
    [stream]
  );

  const resume = useCallback(
    (decision: GateDecision) => {
      stream.submit(null, { command: { resume: decision } });
    },
    [stream]
  );

  const gate: GatePayload | null = useMemo(() => {
    const raw = stream.interrupt as InterruptLike | undefined;
    const payload =
      raw && typeof raw === "object" && "value" in raw ? raw.value : raw;
    if (
      payload &&
      typeof payload === "object" &&
      "gate" in (payload as Record<string, unknown>) &&
      "title" in (payload as Record<string, unknown>)
    ) {
      return payload as GatePayload;
    }
    return null;
  }, [stream.interrupt]);

  return {
    state: stream.values as ResearchState | undefined,
    stream,
    gate,
    start,
    resume,
    connected: Boolean(GATEWAY_URL),
    error: stream.error,
    isLoading: stream.isLoading,
  };
}
