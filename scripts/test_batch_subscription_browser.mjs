// Run after `trunk build --dist /tmp/ccfddl-browser-test`:
// node scripts/test_batch_subscription_browser.mjs /tmp/ccfddl-browser-test
// Uses Chrome's DevTools protocol and only Node.js built-ins.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
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
  ".js": "text/javascript",
  ".json": "application/json",
  ".wasm": "application/wasm",
};
const server = createServer((request, response) => {
  const pathname = new URL(request.url, "http://localhost").pathname;
  if (pathname === "/api/bootstrap") {
    response.writeHead(200, { "Content-Type": "application/json" });
    response.end(JSON.stringify({
      user: { login: "browser-test", avatar_url: "", profile_url: "" },
      counts: {},
      starred: ["cvpr27", "iclr27"],
    }));
    return;
  }
  const file = resolve(dist, `.${pathname === "/" ? "/index.html" : pathname}`);
  if (!file.startsWith(`${dist}${sep}`) && file !== join(dist, "index.html")) {
    response.writeHead(403).end();
    return;
  }
  try {
    response.writeHead(200, { "Content-Type": types[extname(file)] ?? "application/octet-stream" });
    response.end(readFileSync(file));
  } catch {
    response.writeHead(404).end();
  }
});
await new Promise((done) => server.listen(0, "127.0.0.1", done));

const profile = mkdtempSync(join(tmpdir(), "ccfddl-batch-browser-"));
const browser = spawn(chrome, [
  "--headless=new",
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

async function state() {
  return evaluate(`(() => ({
    checked: Object.fromEntries(Array.from(document.querySelectorAll('.batch-subscription-option'))
      .map(row => [row.textContent.trim().split(' ')[0], row.querySelector('input').checked])),
    count: document.querySelector('.batch-subscription-actions span')?.textContent.trim(),
    ids: new URL(document.querySelector('.batch-subscription-url')?.value ?? 'https://example.com')
      .searchParams.getAll('id'),
  }))()`);
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
  await command("Page.addScriptToEvaluateOnNewDocument", {
    source: "localStorage.setItem('language_preference', 'en')",
  });
  await command("Page.navigate", { url: `http://127.0.0.1:${server.address().port}/` });
  await until(() => evaluate("Boolean(document.querySelector('#github-account-menu summary'))"), "account menu");
  await evaluate("document.querySelector('#github-account-menu summary').click()");
  await evaluate("Array.from(document.querySelectorAll('.github-account-options button')).find(button => button.textContent.includes('Batch Subscribe')).click()");
  await until(async () => (await state()).count === "2 / 2", "selected editions");
  assert.deepEqual((await state()).checked, { CVPR: true, ICLR: true });

  await evaluate("Array.from(document.querySelectorAll('.batch-subscription-option')).find(row => row.textContent.includes('ICLR')).querySelector('input').click()");
  await until(async () => (await state()).count === "1 / 2", "manual uncheck");
  await evaluate("document.querySelector('.batch-subscription-actions button:first-child').click()");
  await until(async () => (await state()).count === "2 / 2", "Select all");
  assert.deepEqual(await state(), {
    checked: { CVPR: true, ICLR: true },
    count: "2 / 2",
    ids: ["cvpr27", "iclr27"],
  });

  await evaluate("Array.from(document.querySelectorAll('.batch-subscription-option')).find(row => row.textContent.includes('ICLR')).querySelector('input').click()");
  await evaluate("Array.from(document.querySelectorAll('.batch-subscription-option')).find(row => row.textContent.includes('ICLR')).querySelector('input').click()");
  await evaluate("document.querySelector('.batch-subscription-actions button:nth-child(2)').click()");
  await until(async () => (await state()).count === "0 / 2", "Clear");
  assert.deepEqual(await state(), {
    checked: { CVPR: false, ICLR: false },
    count: "0 / 2",
    ids: [],
  });
  console.log("Batch subscription checkbox browser regression passed");
} finally {
  socket?.close();
  browser.kill();
  await new Promise((done) => server.close(done));
  rmSync(profile, { recursive: true, force: true });
}
