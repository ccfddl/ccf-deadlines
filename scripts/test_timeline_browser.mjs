// Run after building the site: node scripts/test_timeline_browser.mjs dist
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
  ".svg": "image/svg+xml",
  ".js": "text/javascript",
  ".json": "application/json",
  ".wasm": "application/wasm",
};
const testDeadline = '2026-11-11 19:59:00';
const testConferences = () => [{
  title: 'TIMELINETEST', description: 'Timeline interaction regression', sub: 'AI',
  rank: {ccf: 'A'}, dblp: 'test',
  confs: [{year: 2027, id: 'timelinetest27', link: 'https://example.org',
    timeline: [{abstract_deadline: '2026-10-05 19:59:00', deadline: testDeadline, rebuttal_deadline: '2027-01-15 19:59:00', decision_deadline: '2027-02-11 19:59:00'}], timezone: 'UTC',
    date: 'June 20-25, 2027', opening: '2027-06-20 08:00:00', place: 'Virtual'},
  ],
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
  await command("Emulation.setFocusEmulationEnabled", {enabled: true});
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
    window.openingTestNow = RealDate.parse('2026-10-04T00:00:00Z');
    globalThis.Date = class extends RealDate {
      constructor(...args) { super(...(args.length ? args : [window.openingTestNow])); }
      static now() { return window.openingTestNow; }
    };
  `});
  const present = () => evaluate("[...document.querySelectorAll('.conf-title')].some(node => node.textContent.trim() === 'TIMELINETEST 2027')");
  const bounds = () => evaluate(`(() => {
    const container = document.querySelector('.conference-detail-timeline .all_line');
    const preview = container.querySelector('.timeline-preview');
    if (!preview) return null;
    const box = preview.getBoundingClientRect(), outer = container.getBoundingClientRect();
    return {text: preview.textContent.trim(), left:box.left, right:box.right, width:box.width,
      containerLeft:outer.left, containerRight:outer.right,
      clipped:preview.scrollWidth > preview.clientWidth,
      now:getComputedStyle(container.querySelector('.sel_dot')).visibility,
      align:getComputedStyle(container.querySelector('.timeline-preview-slot')).justifyContent};
  })()`);
  for (const mode of ['cards', 'list']) {
    const preferences = await command('Page.addScriptToEvaluateOnNewDocument', {source: `
      localStorage.setItem('conference_view', '${mode}');
      localStorage.setItem('conference_search', 'TIMELINETEST');
      localStorage.setItem('display_timezone', 'UTC');
      localStorage.setItem('show_past', 'false');
      for (const key of ['types', 'ranks', 'core_ranks', 'thcpl_ranks']) localStorage.setItem(key, '[]');
    `});
    for (const width of [1280, 390, 320]) {
      await command('Emulation.setDeviceMetricsOverride', {width, height: 1100, deviceScaleFactor: 1, mobile:false});
      await command('Page.navigate', {url: `http://127.0.0.1:${server.address().port}/?filters=all`});
      await until(present, 'conference loaded');
      await evaluate("document.querySelector('.conf-title').click()");
      await until(() => evaluate("document.querySelectorAll('.conference-detail-timeline .timeline-event').length === 5"), 'timeline buttons');
      assert.equal(await evaluate("getComputedStyle(document.querySelector('.conference-detail-timeline .sel_dot')).visibility"), 'visible');
      // Click every marker. First and last labels must remain within the rail bounds.
      for (let index=0; index<5; index++) {
        await evaluate(`document.querySelectorAll('.conference-detail-timeline .timeline-event')[${index}].click()`);
        await until(bounds, 'selected preview');
        const preview=await bounds();
        assert.equal(preview.now, 'hidden');
        assert.ok(preview.left >= preview.containerLeft-1 && preview.right <= preview.containerRight+1, JSON.stringify(preview));
        assert.equal(preview.clipped, false);
        if (index===0) assert.equal(preview.align, 'flex-start');
        if (index===4) assert.equal(preview.align, 'flex-end');
        if (index===0 || index===4) {
          const screenshot = await command('Page.captureScreenshot', {format:'png'});
          writeFileSync(`/tmp/ccfddl-timeline-${mode}-${width}-${index}.png`, Buffer.from(screenshot.data,'base64'));
        }
        // Clicking the selected marker again dismisses it and restores NOW.
        await evaluate(`document.querySelectorAll('.conference-detail-timeline .timeline-event')[${index}].click()`);
        await until(() => evaluate("!document.querySelector('.conference-detail-timeline .timeline-preview')"), 'toggle dismissal');
        assert.equal(await evaluate("getComputedStyle(document.querySelector('.conference-detail-timeline .sel_dot')).visibility"), 'visible');
      }
      // A separate click dismisses the selection.
      await evaluate("document.querySelector('.conference-detail-timeline .timeline-event').click()");
      await evaluate("document.querySelector('.conference-detail-description').click()");
      await until(() => evaluate("!document.querySelector('.conference-detail-timeline .timeline-preview')"), 'outside dismissal');
      // Keyboard focus previews the node, Escape dismisses without closing the dialog.
      await evaluate("document.querySelector('.conference-detail-timeline .timeline-event').blur(); document.querySelector('.conference-detail-timeline .timeline-event').focus()");
      await until(bounds, 'keyboard preview');
      assert.equal((await bounds()).now,'hidden');
      await command('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
      await until(() => evaluate("!document.querySelector('.conference-detail-timeline .timeline-preview')"), 'Escape dismissal');
      assert.equal(await evaluate("Boolean(document.querySelector('.conference-detail-title'))"), true);
      // Physical hover also works beside the NOW marker and restores it on leave.
      const point = await evaluate(`(() => {
        const box = document.querySelector('.conference-detail-timeline .timeline-event').getBoundingClientRect();
        return {x: box.left+box.width/2, y:box.top+box.height/2};
      })()`);
      await command('Input.dispatchMouseEvent',{type:'mouseMoved',...point});
      await until(bounds,'hover preview');
      assert.equal((await bounds()).now,'hidden');
      await command('Input.dispatchMouseEvent',{type:'mouseMoved',x:1,y:1});
      await until(() => evaluate("!document.querySelector('.conference-detail-timeline .timeline-preview')"),'hover dismissal');
      assert.equal(await evaluate("getComputedStyle(document.querySelector('.conference-detail-timeline .sel_dot')).visibility"),'visible');
      if (width === 320) {
        await command('Emulation.setTouchEmulationEnabled',{enabled:true});
        await command('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[point]});
        await command('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
        await until(bounds,'touch selection');
        assert.equal((await bounds()).now,'hidden');
        const outside = await evaluate(`(() => {
          const box = document.querySelector('.conference-detail-description').getBoundingClientRect();
          return {x:box.left+10,y:box.top+box.height/2};
        })()`);
        await command('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[outside]});
        await command('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
        await until(() => evaluate("!document.querySelector('.conference-detail-timeline .timeline-preview')"),'touch outside dismissal');
        await command('Emulation.setTouchEmulationEnabled',{enabled:false});
      }
      assert.equal(await evaluate('document.documentElement.scrollWidth > innerWidth'), false);
      console.log('Timeline selection, dismissal and label bounds passed:',mode,width);
    }
    await command('Page.removeScriptToEvaluateOnNewDocument',{identifier:preferences.identifier});
  }
  assert.deepEqual(errors, []);
  console.log('Timeline labels stay visible and NOW hides during interaction');
} finally {
  socket?.close();
  browser.kill();
  await new Promise(done => browser.once('exit', done));
  server.closeAllConnections();
  await new Promise(done => server.close(done));
  rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}
