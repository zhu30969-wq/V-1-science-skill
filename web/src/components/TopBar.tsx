"use client";

import { APP_NAME } from "@/lib/api";

export default function TopBar({
  campaignId,
  connected,
}: {
  campaignId?: string;
  connected: boolean;
}) {
  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark">⟳</span>
        <h1>{APP_NAME}</h1>
      </div>
      <div className="topbar-meta">
        <span className="campaign">
          Campaign: <b>{campaignId || "—"}</b>
        </span>
        <span className={`conn ${connected ? "conn-ok" : "conn-off"}`}>
          {connected ? "● gateway connected" : "○ gateway not configured"}
        </span>
      </div>
    </header>
  );
}
