// Run after building the site: node scripts/test_conference_opening_browser.mjs dist
// Uses Chrome's DevTools protocol and only Node.js built-ins.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { extname, join, resolve, sep } from "node:path";
import { setTimeout as delay } from "node:timers/promises";

const dist = resolve(process.argv[2] ?? "dist");
const chrome = process.env.CHROME_BINARY ?? [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
].find(existsSync);
if (!chrome || !existsSync(join(dist, "index.html"))) {
  throw new Error("Build the site and provide a valid dist directory and Chrome binary");
}

const types = {
  ".css": "text/css",
  ".html": "text/html",
  ".ico": "image/x-icon",
  ".svg": "image/svg+xml",
  ".js": "text/javascript",
  ".json": "application/json",
  ".wasm": "application/wasm",
};
let testDeadline = '2027-06-20 07:59:55';
const testConferences = () => [{
  title: 'OPENINGTEST', description: 'Opening transition regression', sub: 'AI',
  rank: {ccf: 'A'}, dblp: 'test',
  confs: [{year: 2027, id: 'openingtest27', link: 'https://example.org',
    timeline: [{deadline: testDeadline}], timezone: 'UTC',
    date: 'June 20-25, 2027', opening: '2027-06-20 08:00:00', place: 'Virtual'}],
}];
const server = createServer((request, response) => {
  const pathname = new URL(request.url, "http://localhost").pathname;
  if (pathname === '/conference/initial.json') {
    response.writeHead(200, {'Content-Type': 'application/json'});
    response.end(JSON.stringify({conferences: testConferences(), archive: null}));
    return;
  }
  if (pathname === "/api/bootstrap") {
    response.writeHead(200, { "Content-Type": "application/json" });
    response.end(JSON.stringify({
      user: { login: "browser-test", avatar_url: "", profile_url: "" },
      counts: {},
      starred: [],
    }));
    return;
  }
  let file = resolve(dist, `.${pathname === "/" ? "/index.html" : pathname}`);
  if (!file.startsWith(`${dist}${sep}`) && file !== join(dist, "index.html")) {
    response.writeHead(403).end();
    return;
  }
  try {
    if (statSync(file).isDirectory()) file = join(file, "index.html");
    response.writeHead(200, { "Content-Type": types[extname(file)] ?? "application/octet-stream" });
    response.end(readFileSync(file));
  } catch {
    response.writeHead(404).end();
  }
});
await new Promise((done) => server.listen(0, "127.0.0.1", done));

const profile = mkdtempSync(join(tmpdir(), "ccfddl-opening-browser-"));
const browser = spawn(chrome, [
  "--headless=new", "--disable-extensions", "--no-first-run", "--no-default-browser-check",
  "--no-sandbox",
  "--disable-gpu",
  "--disable-dev-shm-usage",
  "--remote-debugging-port=0",
  `--user-data-dir=${profile}`,
  "about:blank",
], { stdio: "ignore" });
let socket;
let nextId = 0;
const pending = new Map();

async function until(check, label, timeout = 20_000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const result = await check();
    if (result) return result;
    await delay(100);
  }
  throw new Error(`Timed out waiting for ${label}`);
}

function command(method, params = {}) {
  const id = ++nextId;
  return new Promise((resolveCommand, rejectCommand) => {
    pending.set(id, { resolveCommand, rejectCommand });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  const result = await command("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text);
  }
  return result.result.value;
}

try {
  const portFile = join(profile, "DevToolsActivePort");
  const debugPort = await until(() => existsSync(portFile) && readFileSync(portFile, "utf8").split("\n")[0], "Chrome debugging port");
  const targets = await fetch(`http://127.0.0.1:${debugPort}/json/list`).then((res) => res.json());
  const target = targets.find((item) => item.type === "page");
  assert.ok(target, "Chrome page target must exist");
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((done, fail) => {
    socket.addEventListener("open", done, { once: true });
    socket.addEventListener("error", fail, { once: true });
  });
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    const waiting = pending.get(message.id);
    if (!waiting) return;
    pending.delete(message.id);
    if (message.error) waiting.rejectCommand(new Error(message.error.message));
    else waiting.resolveCommand(message.result);
  });
  await command("Page.enable");
  await command("Runtime.enable");
  await command("Emulation.setTimezoneOverride", {timezoneId: "UTC"});
  await command("Page.addScriptToEvaluateOnNewDocument", {
    source: "localStorage.setItem('language_preference', 'en')",
  });
  const errors = [];
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.method === 'Runtime.exceptionThrown') { errors.push(message.params.exceptionDetails.text); console.error(JSON.stringify(message.params.exceptionDetails)); }
  });

  await command('Page.addScriptToEvaluateOnNewDocument', {source: `
    const RealDate = Date;
    window.openingTestNow = RealDate.parse('2027-06-20T07:59:50Z');
    globalThis.Date = class extends RealDate {
      constructor(...args) { super(...(args.length ? args : [window.openingTestNow])); }
      static now() { return window.openingTestNow; }
    };
  `});
  const present = () => evaluate("[...document.querySelectorAll('.conf-title')].some(node => node.textContent.trim() === 'OPENINGTEST 2027')");
  const nextLabel = () => evaluate("document.querySelector('.conference-detail-deadline.is-next .conference-detail-deadline-name')?.textContent.trim() ?? ''");
  for (const mode of ['cards', 'list']) {
    for (const showPast of [false, true]) {
      for (const deadline of ['2027-06-20 07:59:55', 'TBD']) {
        testDeadline = deadline;
        const preferences = await command('Page.addScriptToEvaluateOnNewDocument', {source: `
          localStorage.setItem('conference_view', '${mode}');
          localStorage.setItem('conference_search', 'OPENINGTEST');
          localStorage.setItem('display_timezone', 'UTC');
          localStorage.setItem('show_past', '${showPast}');
          localStorage.setItem('sort_by_stars', 'false');
          for (const key of ['types', 'ranks', 'core_ranks', 'thcpl_ranks']) localStorage.setItem(key, '[]');
        `});
        await command('Page.navigate', {url: `http://127.0.0.1:${server.address().port}/?filters=all`});
        await until(present, 'conference before opening');
        await evaluate("document.querySelector('.conf-title').click()");
        await until(async () => (await nextLabel()).includes(deadline === 'TBD' ? 'Conference Opening' : 'Paper Submission'), 'initial next deadline');
        await evaluate("window.openingTestNow = Date.parse('2027-06-20T07:59:56Z')");
        await until(async () => (await nextLabel()).includes('Conference Opening'), 'submission transitions to opening without reloading', 5000);
        const fixedReference = showPast && deadline !== 'TBD';
        if (fixedReference) {
          await evaluate(`(() => { const input = document.querySelector('#base-time-input');
            input.value = '2027-06-20T07:59:56';
            input.dispatchEvent(new Event('change', {bubbles: true})); })()`);
        }
        await evaluate("window.openingTestNow = Date.parse('2027-06-20T08:00:00Z')");
        if (fixedReference) {
          await delay(1500);
          assert.match(await nextLabel(), /Conference Opening/, 'custom base time remains frozen');
          await evaluate(`(() => { const input = document.querySelector('#base-time-input');
            input.value = '';
            input.dispatchEvent(new Event('change', {bubbles: true})); })()`);
        }
        await until(async () => (await nextLabel()) === '', 'open detail updates when opening passes', 5000);
        await evaluate("document.querySelector('.conference-detail-close').click()");
        if (showPast) {
          assert.equal(await present(), true);
          await until(() => evaluate("Boolean(document.querySelector('.conf-fin .conference-card-passed'))"), 'finished conference stays visible', 5000);
        } else {
          await until(async () => !(await present()), 'finished conference disappears with past hidden', 5000);
        }
        await command('Page.removeScriptToEvaluateOnNewDocument', {identifier: preferences.identifier});
        console.log('Opening transition passed:', mode, showPast, deadline);
      }
    }
  }
  assert.deepEqual(errors, []);
  console.log('Live submission/opening transitions passed in cards and list views, with known/TBD submissions and past visibility on/off');
} finally {
  socket?.close();
  browser.kill();
  await new Promise(done => browser.once('exit', done));
  server.closeAllConnections();
  await new Promise(done => server.close(done));
  rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}
