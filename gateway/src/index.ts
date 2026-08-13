/**
 * STOV AI Scientist secure gateway (spec PHASE 17, §61).
 *
 * The browser NEVER holds DEEPSEEK_API_KEY / LANGSMITH_API_KEY. This
 * gateway is the only party that knows LANGGRAPH_API_URL and
 * LANGGRAPH_API_KEY; it injects the backend auth server-side and streams
 * responses to the static GitHub Pages frontend.
 *
 * Cloudflare Worker compatible (Hono web-standard API) with a local dev
 * adapter in dev.ts.
 */

import { Hono } from "hono";
import { cors } from "hono/cors";
import { logger } from "hono/logger";

export type Env = {
  /** LangGraph/LangSmith agent server base URL, e.g. https://<deployment>.langgraph.app */
  LANGGRAPH_API_URL: string;
  /** Server-side backend auth (LangSmith API key) — never sent to the browser */
  LANGGRAPH_API_KEY?: string;
  /** Exact frontend origin allowed by CORS (spec §61). No wildcard. */
  ALLOWED_ORIGIN?: string;
  /** Basic rate limit: max requests per window per IP */
  RATE_LIMIT_MAX?: string;
  RATE_LIMIT_WINDOW_SECONDS?: string;
};

const DEFAULT_ALLOWED_ORIGIN = "https://zhu30969-wq.github.io";

// In-memory token bucket (per isolate; sufficient for basic protection)
const buckets = new Map<string, { count: number; resetAt: number }>();

function rateLimited(ip: string, max: number, windowSeconds: number): boolean {
  const now = Date.now();
  const bucket = buckets.get(ip);
  if (!bucket || bucket.resetAt <= now) {
    buckets.set(ip, { count: 1, resetAt: now + windowSeconds * 1000 });
    return false;
  }
  bucket.count += 1;
  if (bucket.count > max) {
    return true;
  }
  return false;
}

export function createGateway(env: Env): Hono {
  const backendUrl = (env.LANGGRAPH_API_URL || "").replace(/\/+$/, "");
  const allowedOrigin = (env.ALLOWED_ORIGIN || DEFAULT_ALLOWED_ORIGIN).split(",").map((o) => o.trim());
  const rateMax = parseInt(env.RATE_LIMIT_MAX || "60", 10);
  const rateWindow = parseInt(env.RATE_LIMIT_WINDOW_SECONDS || "60", 10);

  const app = new Hono();

  app.use("*", logger());

  // Security headers everywhere
  app.use("*", async (c, next) => {
    await next();
    c.header("X-Content-Type-Options", "nosniff");
    c.header("X-Frame-Options", "DENY");
    c.header("Referrer-Policy", "no-referrer");
    c.header("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
    c.header(
      "Content-Security-Policy",
      "default-src 'none'; connect-src 'self' https:; img-src 'self' data: https:"
    );
  });

  // CORS: EXACT origin only — never "*" with an unprotected agent backend
  app.use(
    "*",
    cors({
      origin: (origin) => (origin && allowedOrigin.includes(origin) ? origin : allowedOrigin[0]),
      allowMethods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
      allowHeaders: ["content-type", "x-api-key", "authorization"],
      maxAge: 86400,
    })
  );

  // Basic rate limiting per IP
  app.use("*", async (c, next) => {
    const ip = c.req.header("cf-connecting-ip") || c.req.header("x-forwarded-for") || "local";
    if (rateLimited(ip, rateMax, rateWindow)) {
      return c.json({ error: "rate_limit_exceeded", detail: "too many requests" }, 429);
    }
    await next();
  });

  // Health
  app.get("/healthz", (c) => {
    return c.json({ status: "ok", backend: backendUrl ? "configured" : "missing" });
  });

  // Proxy: forward method, body, and inject backend auth server-side;
  // streaming responses pass through untouched (hono streams by default).
  app.all("*", async (c) => {
    if (!backendUrl) {
      return c.json({ error: "gateway_not_configured", detail: "LANGGRAPH_API_URL missing" }, 503);
    }
    const url = new URL(c.req.url);
    const upstream = new URL(`${backendUrl}${url.pathname}${url.search}`);

    const headers = new Headers(c.req.raw.headers);
    headers.delete("host");
    headers.delete("origin");
    headers.delete("referer");
    headers.delete("cookie");
    // Server-side auth injection (spec §61)
    if (env.LANGGRAPH_API_KEY) {
      headers.set("x-api-key", env.LANGGRAPH_API_KEY);
    }

    let body: BodyInit | null | undefined;
    if (c.req.method !== "GET" && c.req.method !== "HEAD") {
      body = await c.req.raw.arrayBuffer();
    }

    try {
      const upstreamRes = await fetch(upstream.toString(), {
        method: c.req.method,
        headers,
        body,
        redirect: "manual",
      });

      const responseHeaders = new Headers(upstreamRes.headers);
      responseHeaders.delete("set-cookie"); // browser-facing proxy: no backend cookies
      const contentLength = responseHeaders.get("content-length");

      // normalize upstream errors into JSON when the backend produced an error page
      if (upstreamRes.status >= 500) {
        return c.json(
          {
            error: "backend_error",
            detail: `upstream returned ${upstreamRes.status}`,
          },
          502
        );
      }

      return new Response(upstreamRes.body, {
        status: upstreamRes.status,
        headers: responseHeaders,
      });
    } catch (err) {
      const detail = err instanceof Error ? err.message : "unknown error";
      return c.json({ error: "backend_unreachable", detail }, 502);
    }
  });

  return app;
}

export default {
  fetch: (request: Request, env: Env) => {
    const app = createGateway(env);
    return app.fetch(request, env);
  },
};
