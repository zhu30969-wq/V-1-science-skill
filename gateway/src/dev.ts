/**
 * Local development server (terminal 2 of the local E2E stack).
 *
 *   cd gateway && npm install && npm run dev
 *
 * Reads .dev.vars (see .dev.vars.example) and serves on PORT (default 8787).
 */

import { serve } from "@hono/node-server";
import { config } from "dotenv";
import { createGateway, type Env } from "./index";

config({ path: ".dev.vars" });

const env: Env = {
  LANGGRAPH_API_URL: process.env.LANGGRAPH_API_URL || "http://127.0.0.1:2024",
  LANGGRAPH_API_KEY: process.env.LANGGRAPH_API_KEY,
  ALLOWED_ORIGIN: process.env.ALLOWED_ORIGIN || "http://localhost:3000,https://zhu30969-wq.github.io",
  RATE_LIMIT_MAX: process.env.RATE_LIMIT_MAX,
  RATE_LIMIT_WINDOW_SECONDS: process.env.RATE_LIMIT_WINDOW_SECONDS,
};

const port = parseInt(process.env.PORT || "8787", 10);
const app = createGateway(env);

serve({ fetch: app.fetch, port }, (info) => {
  console.log(`[gateway] listening on http://127.0.0.1:${info.port}`);
  console.log(`[gateway] backend -> ${env.LANGGRAPH_API_URL}`);
});
