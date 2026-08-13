/**
 * Gateway tests: CORS exact-origin policy, server-side auth injection,
 * streaming pass-through, rate limiting, error normalization.
 * Uses a local mock upstream (no external network).
 */

import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { serve } from "@hono/node-server";
import { createGateway, type Env } from "../src/index";

const UPSTREAM_PORT = 18791;
const GATEWAY_PORT = 18792;

type DevServer = ReturnType<typeof serve>;

let upstream: DevServer;
let gateway: DevServer;
let receivedHeaders: Record<string, string | undefined> = {};
let upstreamBody = "";

beforeAll(async () => {
  // mock LangGraph agent server
  upstream = serve(
    {
      port: UPSTREAM_PORT,
      fetch: async (req) => {
        receivedHeaders = Object.fromEntries(req.headers.entries());
        upstreamBody = await req.text();
        const url = new URL(req.url);
        if (url.pathname === "/threads" && req.method === "POST") {
          return new Response(JSON.stringify({ thread_id: "t-1", headers_seen: receivedHeaders, body: upstreamBody }), {
            status: 201,
            headers: { "content-type": "application/json" },
          });
        }
        if (url.pathname === "/stream") {
          // streaming response: two chunks
          const encoder = new TextEncoder();
          const stream = new ReadableStream({
            start(controller) {
              controller.enqueue(encoder.encode('{"event":"metadata"}'));
              controller.enqueue(encoder.encode('{"event":"values"}'));
              controller.close();
            },
          });
          return new Response(stream, { headers: { "content-type": "application/x-ndjson" } });
        }
        if (url.pathname === "/boom") {
          return new Response("upstream exploded", { status: 500 });
        }
        return new Response("not found", { status: 404 });
      },
    },
    () => {}
  );

  const env: Env = {
    LANGGRAPH_API_URL: `http://127.0.0.1:${UPSTREAM_PORT}`,
    LANGGRAPH_API_KEY: "secret-backend-key",
    ALLOWED_ORIGIN: "https://zhu30969-wq.github.io",
    RATE_LIMIT_MAX: "5",
    RATE_LIMIT_WINDOW_SECONDS: "60",
  };
  gateway = serve({ port: GATEWAY_PORT, fetch: createGateway(env).fetch }, () => {});
});

afterAll(() => {
  upstream.close();
  gateway.close();
});

const base = `http://127.0.0.1:${GATEWAY_PORT}`;

describe("gateway proxy", () => {
  it("forwards POST bodies and injects backend auth server-side", async () => {
    const res = await fetch(`${base}/threads`, {
      method: "POST",
      headers: { "content-type": "application/json", origin: "https://zhu30969-wq.github.io" },
      body: JSON.stringify({ assistant_id: "stov_scientist" }),
    });
    expect(res.status).toBe(201);
    const payload = (await res.json()) as any;
    expect(payload.thread_id).toBe("t-1");
    // backend auth was injected server-side
    expect(payload.headers_seen["x-api-key"]).toBe("secret-backend-key");
    // the browser request body passed through
    expect(payload.body).toContain("stov_scientist");
  });

  it("streams responses chunk by chunk", async () => {
    const res = await fetch(`${base}/stream`, { headers: { origin: "https://zhu30969-wq.github.io" } });
    expect(res.status).toBe(200);
    const text = await res.text();
    expect(text).toContain('{"event":"metadata"}');
    expect(text).toContain('{"event":"values"}');
  });

  it("normalizes backend 500s into JSON 502", async () => {
    const res = await fetch(`${base}/boom`, { headers: { origin: "https://zhu30969-wq.github.io" } });
    expect(res.status).toBe(502);
    const payload = (await res.json()) as any;
    expect(payload.error).toBe("backend_error");
  });

  it("applies security headers", async () => {
    const res = await fetch(`${base}/healthz`, { headers: { origin: "https://zhu30969-wq.github.io" } });
    expect(res.headers.get("x-content-type-options")).toBe("nosniff");
    expect(res.headers.get("x-frame-options")).toBe("DENY");
  });

  it("rejects CORS for non-whitelisted origins (no wildcard)", async () => {
    const res = await fetch(`${base}/healthz`, { headers: { origin: "https://evil.example.com" } });
    const acao = res.headers.get("access-control-allow-origin");
    // never "*" and never the attacker's origin
    expect(acao).not.toBe("*");
    expect(acao).not.toBe("https://evil.example.com");
  });

  it("rate limits excessive requests", async () => {
    let statuses: number[] = [];
    for (let i = 0; i < 8; i++) {
      const res = await fetch(`${base}/healthz`, { headers: { origin: "https://zhu30969-wq.github.io" } });
      statuses.push(res.status);
    }
    expect(statuses).toContain(429);
  });
});
