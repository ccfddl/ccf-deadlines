import { McpServer } from "@modelcontextprotocol/server";
import { createMcpHandler } from "agents/mcp/server";
import { z } from "zod";

import { CATEGORIES, EVENT_TYPES, getConference, loadCatalog, searchConferencePage, upcomingDeadlinePage } from "./catalog.js";
import { ACCEPTANCE_SOURCE, createAcceptanceIndex, enrichAcceptance, getAcceptanceRates, loadAcceptanceCatalog } from "./acceptance.js";

const filters = {
  category: z.string().trim().min(1).max(10).optional().describe("Subject code; use get_filter_options to discover codes."),
  ccf_rank: z.enum(["A", "B", "C", "N"]).optional().describe("N means unranked."),
  core_rank: z.enum(["A*", "A", "B", "C", "N"]).optional().describe("N means unranked."),
  thcpl_rank: z.enum(["A", "B", "N"]).optional().describe("N means unranked."),
  year: z.number().int().min(1900).max(2200).optional().describe("Conference edition year, which may differ from its submission year."),
};
const pagination = {
  limit: z.number().int().min(1).max(50).optional(),
  offset: z.number().int().min(0).max(100_000).optional().describe("Use next_offset from the previous response to fetch the next page."),
};
const displayTimezone = z.string().trim().min(1).max(100).refine((timezone) => {
  try { new Intl.DateTimeFormat("en", { timeZone: timezone }); return true; }
  catch { return false; }
}, "Use a valid IANA timezone such as Asia/Shanghai, America/New_York, or UTC").optional();

const annotations = { readOnlyHint: true, destructiveHint: false, openWorldHint: false };

function result(data) {
  return {
    content: [{ type: "text", text: JSON.stringify(data) }],
    structuredContent: data,
  };
}

async function withCatalog(operation, { acceptance = false, enrich = false, options = {} } = {}) {
  try {
    const [catalogResult, acceptanceResult] = await Promise.allSettled([
      loadCatalog(), ...(acceptance ? [loadAcceptanceCatalog()] : []),
    ]);
    if (catalogResult.status === "rejected") throw catalogResult.reason;
    const catalog = catalogResult.value;
    if (!acceptance) return result(operation(catalog));
    const acceptanceCatalog = acceptanceResult.status === "fulfilled" ? acceptanceResult.value : undefined;
    if (!acceptanceCatalog) console.error("CCFDDL MCP acceptance error", acceptanceResult.reason?.message ?? "Error");
    const index = createAcceptanceIndex(catalog.conferences, acceptanceCatalog);
    const data = operation(catalog, index);
    return result({ ...(enrich ? enrichAcceptance(data, index, catalog.conferences, options) : data),
      acceptance_data: { status: acceptanceCatalog ? "available" : "unavailable",
        source: ACCEPTANCE_SOURCE, fetched_at: index.fetched_at },
    });
  } catch (error) {
    console.error("CCFDDL MCP catalog error", error?.message ?? "Error");
    return { isError: true, content: [{ type: "text", text: "Conference data is temporarily unavailable." }] };
  }
}

function createServer() {
  const server = new McpServer({ name: "ccfddl", version: "1.2.0" }, {
    instructions: "Use CCFDDL for conference, published deadline and historical acceptance-rate questions. Discover filters with get_filter_options. Return source links, original timezones and UTC instants. Use conference_key or category to distinguish namesakes. Follow next_offset for additional results. Acceptance rates are historical statistics, not predictions for a future edition or individual paper. Include their year and source; report data_issues, ambiguous or unavailable data. Never invent TBD, opening dates or missing statistics.",
  });

  server.registerTool("get_filter_options", {
    title: "Get conference filter options",
    description: "Discover subject codes with English and Chinese names, ranking systems, edition years and deadline types supported by CCFDDL.",
    inputSchema: {},
    annotations,
  }, () => withCatalog(({ conferences, source, fetched_at }) => ({
    categories: CATEGORIES.map((category) => ({ ...category,
      conference_count: conferences.filter((conference) => conference.sub === category.code).length })),
    rankings: { ccf: ["A", "B", "C", "N"], core: ["A*", "A", "B", "C", "N"], thcpl: ["A", "B", "N"] },
    years: [...new Set(conferences.flatMap((conference) => conference.confs.map((edition) => edition.year)))].sort((a, b) => b - a),
    deadline_types: EVENT_TYPES,
    source, fetched_at,
  })));

  server.registerTool("search_conferences", {
    title: "Search conferences",
    description: "Find conferences by name, description or conference_key, subject, CCF/CORE/THCPL rank and edition year. Results include stable keys for namesakes, latest known acceptance-rate statistics up to the selected edition year, total matches and next_offset for pagination. Historical rates always include their own year and source.",
    inputSchema: {
      query: z.string().max(100).optional(),
      ...filters,
      ...pagination,
    },
    annotations,
  }, (args) => withCatalog(({ conferences, source, fetched_at }) => ({
    ...searchConferencePage(conferences, args), source, fetched_at,
  }), { acceptance: true, enrich: true, options: args }));

  server.registerTool("get_conference", {
    title: "Get conference details",
    description: "Get published deadlines, opening, DBLP identifier and historical acceptance statistics by name, name and year, edition ID or conference_key. Includes up to 10 acceptance records, exact-year statistics and two recent records per edition. Use get_acceptance_rates for full history. A namesake lookup returns ambiguous matches: choose a key or category and retry. Optional display_timezone converts known times; TBD remains unchanged.",
    inputSchema: {
      name_or_id: z.string().trim().min(1).max(100),
      category: filters.category,
      year: filters.year,
      edition_limit: z.number().int().min(1).max(20).optional(),
      display_timezone: displayTimezone,
    },
    annotations,
  }, ({ name_or_id, ...options }) => withCatalog(({ conferences, source, fetched_at }) => ({
    conference: getConference(conferences, name_or_id, options), source, fetched_at,
  }), { acceptance: true, enrich: true }));

  server.registerTool("get_acceptance_rates", {
    title: "Get historical conference acceptance rates",
    description: "Read published historical acceptance rates, submitted and accepted paper counts, percentage labels and source links. Accepts conference name, name plus statistical year, edition ID or conference_key. Filter by statistical year or an inclusive year range and paginate newest first. Missing records are not predicted. Ambiguous title-only statistics are not assigned to a namesake. Inspect status and data_issues before comparing rates.",
    inputSchema: {
      name_or_id: z.string().trim().min(1).max(100),
      category: filters.category,
      year: z.number().int().min(1900).max(2200).optional().describe("Acceptance-statistics year; does not require a matching edition in the deadline catalog."),
      from_year: z.number().int().min(1900).max(2200).optional(),
      to_year: z.number().int().min(1900).max(2200).optional(),
      ...pagination,
    },
    annotations,
  }, (args) => {
    if (args.from_year && args.to_year && args.from_year > args.to_year) return {
      isError: true, content: [{ type: "text", text: "from_year must be less than or equal to to_year." }],
    };
    return withCatalog(({ conferences, source, fetched_at }, index) => ({
      ...getAcceptanceRates(conferences, index, args.name_or_id, args), source, fetched_at,
    }), { acceptance: true });
  });

  server.registerTool("upcoming_deadlines", {
    title: "Upcoming conference deadlines",
    description: "List future published nodes in the next 1–365 days, sorted by UTC instant, with latest known historical acceptance statistics up to the edition year. Filter by subject, CCF/CORE/THCPL rank, edition year and deadline_types. Use [deadline] for paper submissions, [abstract_deadline, deadline] for submission nodes, or [opening] for conference openings. Default includes submission, rebuttal and decision nodes, excluding openings. Supports pagination and display_timezone.",
    inputSchema: {
      days: z.number().int().min(1).max(365).optional(),
      ...filters,
      ...pagination,
      deadline_types: z.array(z.enum(EVENT_TYPES)).min(1).max(EVENT_TYPES.length).optional(),
      display_timezone: displayTimezone,
    },
    annotations,
  }, (args) => withCatalog(({ conferences, source, fetched_at }) => ({
    ...upcomingDeadlinePage(conferences, args), source, fetched_at,
  }), { acceptance: true, enrich: true, options: args }));

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
