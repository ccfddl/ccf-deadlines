// Run after `trunk build --dist /tmp/ccfddl-shared-controls`:
// python3 scripts/generate_seo_pages.py --output /tmp/ccfddl-shared-controls
// node scripts/test_conference_controls_browser.mjs /tmp/ccfddl-shared-controls
// Uses Chrome's DevTools protocol and only Node.js built-ins.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
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
let failingDirectoryResource;
const server = createServer((request, response) => {
  const pathname = new URL(request.url, "http://localhost").pathname;
  if ((failingDirectoryResource === 'bootstrap' && /^\/conferences\/app-.*\.js$/.test(pathname))
      || (failingDirectoryResource === 'wasm' && pathname.endsWith('.wasm'))) {
    response.writeHead(503).end();
    return;
  }
  if (pathname === "/api/bootstrap") {
    response.writeHead(200, { "Content-Type": "application/json" });
    response.end(JSON.stringify({
      user: { login: "browser-test", avatar_url: "", profile_url: "" },
      counts: {},
      starred: ["cvpr27", "iclr27"],
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

const profile = mkdtempSync(join(tmpdir(), "ccfddl-controls-browser-"));
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
  const errors = [];
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.method === 'Runtime.exceptionThrown') { errors.push(message.params.exceptionDetails.text); console.error(JSON.stringify(message.params.exceptionDetails)); }
  });
  const metrics = async () => evaluate(`(() => {
    const styles = selector => {
      const node = document.querySelector('.conference-controls ' + selector);
      const css = getComputedStyle(node);
      return Object.fromEntries(['fontFamily', 'fontSize', 'lineHeight', 'height', 'padding', 'borderRadius', 'gap', 'boxSizing'].map(key => [key, css[key]]));
    };
    const controls = document.querySelector('.conference-controls');
    return {
      chip: styles('.thaw-checkbox'), language: styles('.el-switch'),
      search: styles('.thaw-input'), searchInput: styles('.thaw-input__input'), timezone: styles('.toolbar-timezone'),
      rank: styles('.filter-dropdown-trigger'),
      categoryWidth: Math.round(controls.querySelector('.category-filter-grid').getBoundingClientRect().width),
      labels: [...controls.querySelectorAll('.thaw-checkbox__label')].map(node => node.textContent),
      filterToggle: getComputedStyle(controls.querySelector('.toolbar-filter-toggle')).display,
      rankPanel: getComputedStyle(controls.querySelector('.toolbar-rank-filters')).display,
      overflow: document.documentElement.scrollWidth > innerWidth,
    };
  })()`);
  const navigate = async (path, width) => {
    await command('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false });
    console.log('Checking', path, width);
    await command('Page.navigate', { url: `http://127.0.0.1:${server.address().port}${path}` });
    await until(() => evaluate("Boolean(document.querySelector('.conference-controls .filter-dropdown-trigger'))"), 'shared controls');
    await delay(150);
  };
  for (const width of [1280, 768, 390, 320]) {
    let baseline;
    for (const path of ['/?filters=all', '/?view=table&filters=all', '/conferences/?filters=all']) {
      await navigate(path, width);
      const current = await metrics();
      assert.equal(current.overflow, false, `${path} overflow at ${width}px`);
      if (!baseline) baseline = current;
      else assert.deepEqual(current, baseline, `control presentation must match at ${width}px on ${path}`);
      assert.equal(current.labels.length, 10);
      // Only the outer search control draws a frame, including while typing.
      for (const focused of [false, true]) {
        const frame = await evaluate(`(() => {
          const input = document.querySelector('.toolbar-search input');
          if (${focused}) input.focus(); else input.blur();
          const css = getComputedStyle(input);
          const outer = getComputedStyle(input.closest('.thaw-input'));
          return {
            border: css.borderWidth, outline: css.outlineWidth,
            shadow: css.boxShadow, outerBorder: outer.borderWidth,
          };
        })()`);
        assert.deepEqual(frame, {
          border: '0px', outline: '0px', shadow: 'none', outerBorder: '1px',
        }, `${path} search must have a single frame at ${width}px (focused=${focused})`);
      }
      await evaluate("document.querySelector('.toolbar-search input').blur()");
      if (path.includes('/conferences/')) {
        assert.ok(await evaluate("document.querySelector('.directory-list li:not([hidden])').getBoundingClientRect().top < innerHeight"), 'directory links must be visible below the controls');
      }
      assert.equal(current.filterToggle === 'none', width > 768);
      if (width <= 768) {
        assert.ok(current.labels.every(label => label.length === 2));
        assert.equal(current.rankPanel, 'none');
        await evaluate("document.querySelector('.toolbar-filter-toggle').click()");
        await until(() => evaluate("getComputedStyle(document.querySelector('.toolbar-rank-filters')).display === 'flex'"), 'mobile rank panel');
      }
      const screenshot = await command('Page.captureScreenshot', { format: 'png' });
      const name = path.includes('conferences') ? 'directory' : path.includes('view=table') ? 'tabular' : 'main';
      writeFileSync(`/tmp/ccfddl-controls-${name}-${width}.png`, Buffer.from(screenshot.data, 'base64'));
    }
  }
  await navigate('/conferences/?categories=AI&ccf=A&q=ACL&tz=UTC', 1280);
  const visible = () => evaluate("[...document.querySelectorAll('.directory-list li:not([hidden])')].map(row => row.textContent.trim())");
  assert.ok((await visible()).length > 0);
  assert.ok((await visible()).every(title => /^ACL \d{4}$/.test(title)));
  // URL filters override the persisted preferences and survive reload.
  await evaluate("document.querySelector('.toolbar-search input').value = 'no-such-conference'; document.querySelector('.toolbar-search input').dispatchEvent(new Event('input', {bubbles: true}))");
  await until(() => evaluate("!document.querySelector('#directory-empty').hidden"), 'directory empty state');
  assert.equal(await evaluate("new URLSearchParams(location.search).get('q')"), 'no-such-conference');
  await command('Page.reload');
  await until(() => evaluate("document.querySelector('.toolbar-search input')?.value === 'no-such-conference'"), 'persisted search');
  await evaluate("document.querySelector('.toolbar-search input').value = ''; document.querySelector('.toolbar-search input').dispatchEvent(new Event('input', {bubbles: true}))");
  await until(async () => (await visible()).length > 0, 'reset search');
  await evaluate("document.querySelector('.clear-filter').click()");
  await until(() => evaluate("!document.querySelector('.category-filter-grid .filter-selected')"), 'clear category');
  // Rank selectors and timezone picker are the exact main-site components.
  await evaluate("document.querySelector('.filter-dropdown-trigger').click()");
  await until(() => evaluate("Boolean(document.querySelector('.filter-dropdown-panel'))"), 'rank menu');
  await evaluate("document.querySelector('.filter-dropdown-panel .filter-dropdown-clear').click()");
  await until(() => evaluate("!new URLSearchParams(location.search).has('ccf')"), 'clear rank');
  await evaluate("document.querySelector('.toolbar-timezone-trigger').click()");
  await until(() => evaluate("Boolean(document.querySelector('.toolbar-timezone-menu'))"), 'timezone menu');
  await evaluate("[...document.querySelectorAll('.toolbar-timezone-option')].find(node => node.textContent === 'Asia/Shanghai').click()");
  await until(() => evaluate("new URLSearchParams(location.search).get('tz') === 'Asia/Shanghai'"), 'timezone change');
  await evaluate("document.querySelector('.language-switches input').click()");
  await until(() => evaluate("document.documentElement.lang === 'zh-CN'"), 'language change');
  assert.equal(await evaluate("document.querySelector('#directory-empty').textContent"), '没有匹配的会议。');
  await evaluate("[...document.querySelectorAll('.category-filter-grid .checkbox-item')].find(node => node.textContent.includes('人工智能')).querySelector('input').click()");
  await until(() => evaluate("new URLSearchParams(location.search).get('categories') === 'AI'"), 'category selection');
  await navigate('/?view=table', 390);
  assert.equal(await evaluate("document.querySelector('.toolbar-timezone-trigger').textContent.includes('Asia/Shanghai')"), true);
  assert.equal(await evaluate("document.querySelectorAll('.category-filter-grid .filter-selected').length"), 1);
  // Main-site history switch must toggle once when either the text or switch is clicked.
  await navigate('/', 390);
  const past = () => evaluate("document.querySelector('.past-switch input').checked");
  const before = await past();
  await evaluate("document.querySelector('.past-label').click()");
  await until(async () => await past() !== before, 'past label toggle');
  await evaluate("document.querySelector('.past-switch input').click()");
  await until(async () => await past() === before, 'past switch toggle');
  assert.deepEqual(errors, []);
  // A missing bootstrap or WASM must leave usable static links and a working retry.
  for (const resource of ['bootstrap', 'wasm']) {
    failingDirectoryResource = resource;
    await command('Page.navigate', { url: `http://127.0.0.1:${server.address().port}/conferences/` });
    await until(() => evaluate("Boolean(document.querySelector('.directory-controls-loading button'))"), `${resource} failure feedback`);
    assert.ok(await evaluate("document.querySelectorAll('.directory-list a').length > 0"));
    assert.equal(await evaluate("getComputedStyle(document.querySelector('.directory-categories')).display"), 'flex');
    assert.equal(await evaluate("document.querySelector('.directory-controls-loading').getAttribute('role')"), 'alert');
    failingDirectoryResource = undefined;
    await evaluate("document.querySelector('.directory-controls-loading button').click()");
    await until(() => evaluate("Boolean(document.querySelector('.conference-controls .toolbar-search input'))"), `${resource} retry recovery`);
    assert.equal(await evaluate("Boolean(document.querySelector('.directory-controls-loading'))"), false);
  }
  console.log('Shared conference controls passed at 1280, 768, 390 and 320px; directory filtering and cross-view preferences passed');
} finally {
  socket?.close();
  browser.kill();
  await new Promise(done => browser.once('exit', done));
  server.closeAllConnections();
  await new Promise(done => server.close(done));
  rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}
