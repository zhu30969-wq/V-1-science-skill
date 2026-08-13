/** Gateway client wiring (spec §57: buttons must perform REAL resume). */

import { Client } from "@langchain/langgraph-sdk";
import type { GateDecision } from "./types";

export const GATEWAY_URL = process.env.NEXT_PUBLIC_GATEWAY_URL || "";
export const ASSISTANT_ID = process.env.NEXT_PUBLIC_ASSISTANT_ID || "stov_scientist";
export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || "STOV AI Scientist";

export const gatewayConfigured = Boolean(GATEWAY_URL);

export function makeClient(): Client | null {
  if (!gatewayConfigured) return null;
  return new Client({ apiUrl: GATEWAY_URL });
}

export function buildStartInput(payload: Record<string, unknown>): string {
  return JSON.stringify(payload);
}

export function buildResumeCommand(decision: GateDecision) {
  return {
    resume: decision,
  };
}
