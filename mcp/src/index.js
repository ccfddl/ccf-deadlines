import { McpServer } from "@modelcontextprotocol/server";
import { createMcpHandler } from "agents/mcp/server";
import { z } from "zod";

import { getConference, loadCatalog, searchConferences, upcomingDeadlines } from "./catalog.js";

const annotations = { readOnlyHint: true, destructiveHint: false, openWorldHint: false };

function result(data) {
  return {
    content: [{ type: "text", text: JSON.stringify(data) }],
    structuredContent: data,
  };
}

async function withCatalog(operation) {
  try {
    const catalog = await loadCatalog();
    return result(operation(catalog));
  } catch (error) {
    console.error("CCFDDL MCP catalog error", error?.message ?? "Error");
    return { isError: true, content: [{ type: "text", text: "Conference data is temporarily unavailable." }] };
  }
}

function createServer() {
  const server = new McpServer({ name: "ccfddl", version: "1.0.0" }, {
    instructions: "Use CCFDDL for conference and submission deadline questions. Return the conference source link, original timezone, and UTC time. Never invent TBD or missing deadlines.",
  });

  server.registerTool("search_conferences", {
    title: "Search conferences",
    description: "Find conferences by name, CCF rank, and subject category. Use this before requesting details when the conference identifier is unknown.",
    inputSchema: {
      query: z.string().max(100).optional(),
      category: z.string().max(10).optional(),
      ccf_rank: z.enum(["A", "B", "C"]).optional(),
      limit: z.number().int().min(1).max(50).optional(),
    },
    annotations,
  }, (args) => withCatalog(({ conferences, source, fetched_at }) => ({
    results: searchConferences(conferences, args), source, fetched_at,
  })));

  server.registerTool("get_conference", {
    title: "Get conference details",
    description: "Get published deadline nodes by conference name (for example ICLR), name and year (ICLR 2027), or edition ID (iclr27). Date-only and TBD values retain their precision and have no UTC instant.",
    inputSchema: { name_or_id: z.string().trim().min(1).max(100) },
    annotations,
  }, ({ name_or_id }) => withCatalog(({ conferences, source, fetched_at }) => ({
    conference: getConference(conferences, name_or_id), source, fetched_at,
  })));

  server.registerTool("upcoming_deadlines", {
    title: "Upcoming conference deadlines",
    description: "List future conference deadline nodes in the next 1 to 365 days, with original timezone and precision. Date-only nodes have deadline_date and no UTC instant; their possible calendar-day range overlaps the requested window. Can filter by CCF rank and subject category.",
    inputSchema: {
      days: z.number().int().min(1).max(365).optional(),
      category: z.string().max(10).optional(),
      ccf_rank: z.enum(["A", "B", "C"]).optional(),
      limit: z.number().int().min(1).max(50).optional(),
    },
    annotations,
  }, (args) => withCatalog(({ conferences, source, fetched_at }) => ({
    results: upcomingDeadlines(conferences, args), source, fetched_at,
  })));

  return server;
}

export default {
  fetch(request, env, context) {
    const url = new URL(request.url);
    if (url.pathname === "/health" && request.method === "GET") {
      return Response.json({ ok: true });
    }
    if (url.pathname === "/.well-known/openai-apps-challenge" && request.method === "GET") {
      return env.OPENAI_DOMAIN_VERIFICATION_TOKEN
        ? new Response(env.OPENAI_DOMAIN_VERIFICATION_TOKEN, { headers: { "Content-Type": "text/plain; charset=utf-8" } })
        : new Response("Not configured", { status: 404 });
    }
    if (url.pathname !== "/mcp") return new Response("Not found", { status: 404 });

    const hostname = url.hostname;
    const allowedHostnames = ["mcp.ccfddl.com", "localhost", "127.0.0.1"];
    if (hostname.endsWith(".workers.dev")) allowedHostnames.push(hostname);
    return createMcpHandler(createServer, {
      allowedHostnames,
      allowedOriginHostnames: ["chatgpt.com", "mcp.ccfddl.com", "localhost", "127.0.0.1"],
      corsOptions: false,
      responseMode: "json",
    })(request, env, context);
  },
};
