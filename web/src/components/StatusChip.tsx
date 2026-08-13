"use client";

import type { StageStatus } from "@/lib/types";

const STYLES: Record<StageStatus, string> = {
  PENDING: "chip chip-pending",
  RUNNING: "chip chip-running",
  WAITING_FOR_HUMAN: "chip chip-human",
  PASSED: "chip chip-passed",
  FAILED: "chip chip-failed",
  INCONCLUSIVE: "chip chip-inconclusive",
  COMPLETED: "chip chip-completed",
};

export default function StatusChip({ status }: { status: string }) {
  const normalized: StageStatus = (
    {
      PASSED: "PASSED",
      COMPLETED: "COMPLETED",
      FAILED: "FAILED",
      REJECTED: "FAILED",
      INCONCLUSIVE: "INCONCLUSIVE",
      WAITING: "WAITING_FOR_HUMAN",
    } as Record<string, StageStatus>
  )[status] ?? "PENDING";
  return <span className={STYLES[normalized]}>{status}</span>;
}
