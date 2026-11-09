// Run after building the site: node scripts/test_conference_opening_browser.mjs dist
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
let testDeadline = '2027-06-20 07:59:55';
let submissionConferences = null;
const testConferences = () => submissionConferences ?? [{
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
          localStorage.setItem('submission_only', 'false');
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
  const submissionFixture = () => [{
    title: 'OPENINGTEST', description: 'Submission scope regression', sub: 'AI',
    rank: {ccf: 'A'}, dblp: 'test',
    confs: [{year: 2027, id: 'openingtest27', link: 'https://example.org',
      timeline: [
        {abstract_deadline: '2027-06-20 07:59:55', deadline: '2027-06-20 08:00:00',
          rebuttal_deadline: '2027-06-20 08:00:05', decision_deadline: '2027-06-20 08:00:10'},
        {abstract_deadline: '2027-06-20 08:00:15', deadline: '2027-06-20 08:00:20',
          rebuttal_deadline: '2027-06-21 08:00:00', decision_deadline: '2027-06-22 08:00:00'},
      ], timezone: 'UTC', date: 'July 1-5, 2027', opening: '2027-07-01 08:00:00', place: 'Virtual'}],
  }, {
    title: 'ORDERTEST', description: 'Submission sorting regression', sub: 'AI',
    rank: {ccf: 'A'}, dblp: 'test',
    confs: [{year: 2027, id: 'ordertest27', link: 'https://example.org',
      timeline: [{deadline: '2027-06-20 08:00:08'}], timezone: 'UTC',
      date: 'July 3-5, 2027', opening: '2027-07-03 08:00:00', place: 'Virtual'}],
  }];
  async function pointerClick(selector) {
    const point = await until(() => evaluate(`(() => {
      if (document.querySelector('.thaw-dialog-surface.fade-in-scale-up-transition-enter-active, .thaw-dialog-surface.fade-in-scale-up-transition-leave-active')) return null;
      const element = document.querySelector(${JSON.stringify(selector)});
      if (!element) return null;
      element.scrollIntoView({block: 'center'});
      const rect = element.getBoundingClientRect();
      const point = {x: rect.x + rect.width / 2, y: rect.y + rect.height / 2};
      const hit = document.elementFromPoint(point.x, point.y);
      return hit === element || element.contains(hit) ? point : null;
    })()`), `physical pointer target ${selector}`);
    await command('Input.dispatchMouseEvent', {type: 'mousePressed', button: 'left', clickCount: 1, ...point});
    await command('Input.dispatchMouseEvent', {type: 'mouseReleased', button: 'left', clickCount: 1, ...point});
  }
  const submissionLabels = () => evaluate("[...document.querySelectorAll('.conference-detail-deadline-name')].map(node => node.textContent.trim())");
  const firstConference = () => evaluate("document.querySelector('.conf-title')?.textContent.trim()");
  const openSubmissionDetail = () => evaluate("[...document.querySelectorAll('.conf-title')].find(node => node.textContent.trim() === 'OPENINGTEST 2027').click()");
  for (const mode of ['cards', 'list']) {
    for (const width of [1280, 320]) {
      submissionConferences = submissionFixture();
      await command('Emulation.setDeviceMetricsOverride', {width, height: 1000, deviceScaleFactor: 1, mobile: false});
      const preferences = await command('Page.addScriptToEvaluateOnNewDocument', {source: `
        localStorage.setItem('conference_view', '${mode}');
        localStorage.setItem('conference_search', '');
        localStorage.setItem('display_timezone', 'UTC');
        localStorage.setItem('show_past', 'false');
        localStorage.setItem('sort_by_stars', 'false');
        localStorage.removeItem('submission_only');
        for (const key of ['types', 'ranks', 'core_ranks', 'thcpl_ranks']) localStorage.setItem(key, '[]');
      `});
      await command('Page.navigate', {url: `http://127.0.0.1:${server.address().port}/`});
      await until(present, 'submission fixture');
      assert.equal(await evaluate("document.querySelector('.submission-only-switch input').checked"), false);
      assert.equal(await evaluate("document.querySelector('.submission-only-switch').textContent.trim()"), 'Show submission only');
      await openSubmissionDetail();
      await until(async () => (await submissionLabels()).some(label => label.includes('Rebuttal')), 'full mode retains rebuttal');
      assert.ok((await submissionLabels()).some(label => label.includes('Conference Opening')));
      await pointerClick('.conference-detail-close');
      await pointerClick('.submission-only-switch input');
      await until(() => evaluate("localStorage.getItem('submission_only') === 'true'"), 'submission preference saved');
      await command('Page.removeScriptToEvaluateOnNewDocument', {identifier: preferences.identifier});
      await command('Page.reload');
      await until(present, 'saved submission mode');
      assert.equal(await evaluate("document.querySelector('.submission-only-switch input').checked"), true);
      await pointerClick('.language-switches input');
      await until(() => evaluate("document.querySelector('.submission-only-switch').textContent.trim() === '仅显示投稿截止'"), 'Chinese switch label');
      await pointerClick('.language-switches input');
      const layout = await evaluate("({width: innerWidth, content: document.documentElement.scrollWidth})");
      assert.ok(layout.content <= layout.width, `switches must fit at ${width}px`);
      const screenshot = await command('Page.captureScreenshot', {format: 'png'});
      writeFileSync(join(tmpdir(), `ccfddl-submission-${mode}-${width}.png`), Buffer.from(screenshot.data, 'base64'));
      await openSubmissionDetail();
      await until(async () => (await submissionLabels()).length === 4, 'only four paired submission dates');
      assert.ok((await submissionLabels()).every(label => /Abstract Submission|Paper Submission/.test(label)));
      assert.match(await nextLabel(), /Round 1 Abstract Submission/);
      await evaluate("window.openingTestNow = Date.parse('2027-06-20T07:59:56Z')");
      await until(async () => (await nextLabel()).includes('Round 1 Paper Submission'), 'abstract switches to paper', 5000);
      await evaluate("window.openingTestNow = Date.parse('2027-06-20T08:00:01Z')");
      await until(async () => (await nextLabel()).includes('Round 2 Abstract Submission'), 'paper switches to next round, skipping rebuttal', 5000);
      await pointerClick('.conference-detail-close');
      await until(async () => (await firstConference()) === 'ORDERTEST 2027', 'sort uses next submission');
      await pointerClick('.submission-only-switch input');
      await until(async () => (await firstConference()) === 'OPENINGTEST 2027', 'full mode sort restores earlier rebuttal');
      await pointerClick('.submission-only-switch input');
      await until(async () => (await firstConference()) === 'ORDERTEST 2027', 'submission sorting restored');
      await openSubmissionDetail();
      await evaluate("window.openingTestNow = Date.parse('2027-06-20T08:00:16Z')");
      await until(async () => (await nextLabel()).includes('Round 2 Paper Submission'), 'next round abstract switches to paper', 5000);
      await evaluate(`(() => { const input = document.querySelector('#base-time-input');
        input.value = '2027-06-20T08:00:16'; input.dispatchEvent(new Event('change', {bubbles: true})); })()`);
      await evaluate("window.openingTestNow = Date.parse('2027-06-20T08:00:20Z')");
      await delay(1200);
      assert.match(await nextLabel(), /Round 2 Paper Submission/, 'custom reference freezes selected submission');
      await evaluate(`(() => { const input = document.querySelector('#base-time-input');
        input.value = ''; input.dispatchEvent(new Event('change', {bubbles: true})); })()`);
      await until(async () => (await nextLabel()) === '', 'last paper ends submission scope', 5000);
      await pointerClick('.conference-detail-close');
      await until(async () => !(await present()), 'ended submissions hidden before conference opening', 5000);
      await pointerClick('.past-switch input');
      await until(present, 'past submissions can be shown');
      await openSubmissionDetail();
      assert.equal((await submissionLabels()).length, 4);
      assert.ok((await submissionLabels()).every(label => /Abstract Submission|Paper Submission/.test(label)));
      await pointerClick('.conference-detail-close');
      await pointerClick('.submission-only-switch input');
      await openSubmissionDetail();
      await until(async () => (await nextLabel()).includes('Rebuttal'), 'full mode restores upcoming rebuttal');
      assert.ok((await submissionLabels()).some(label => label.includes('Conference Opening')));
      await pointerClick('.conference-detail-close');
      console.log('Submission-only switch, persistence, paired dates, sorting and transitions passed:', mode, width);
    }
  }
  // Missing submission dates remain visible without an opening placeholder; an
  // actual opening still expires them even though that marker is not displayed.
  for (const estimates of [false, true]) {
    submissionConferences = submissionFixture().slice(0, 1);
    const conference = submissionConferences[0];
    const edition = conference.confs[0];
    edition.timeline = [{deadline: 'TBD'}];
    edition.opening = '2027-06-20 08:00:00';
    if (estimates) {
      conference.confs.push({...edition, year: 2026, id: 'openingtest26',
        timeline: [{abstract_deadline: '2026-06-15 23:59:59', deadline: '2026-06-20 23:59:59'}],
        opening: '2026-06-20 08:00:00'});
    }
    const preferences = await command('Page.addScriptToEvaluateOnNewDocument', {source: `
      localStorage.setItem('conference_view', 'cards');
      localStorage.setItem('show_past', 'false');
      localStorage.setItem('submission_only', 'true');
    `});
    await command('Page.navigate', {url: `http://127.0.0.1:${server.address().port}/`});
    await until(present, 'TBD submission remains visible');
    await openSubmissionDetail();
    await until(() => evaluate("document.querySelector('.conference-detail-next strong')?.textContent.trim() === 'TBD'"), 'TBD next deadline');
    assert.equal(await evaluate("document.querySelector('.conference-detail-dialog').textContent.includes('Conference Opening')"), false);
    if (estimates) {
      const labels = await submissionLabels();
      assert.deepEqual(labels, ['Estimated Abstract SubmissionEST.', 'Estimated Paper SubmissionEST.']);
    } else {
      assert.equal(await evaluate("document.querySelector('.conference-detail-dialog').textContent.includes('Dates to be announced')"), true);
    }
    await evaluate("window.openingTestNow = Date.parse('2027-06-20T08:00:00Z')");
    await until(() => evaluate("document.querySelector('.conference-detail-next strong')?.textContent.trim() === 'Passed'"), 'hidden opening expires TBD submission', 5000);
    await pointerClick('.conference-detail-close');
    await until(async () => !(await present()), 'expired TBD edition disappears', 5000);
    await command('Page.removeScriptToEvaluateOnNewDocument', {identifier: preferences.identifier});
    console.log('Submission-only TBD/estimated regression passed:', estimates);
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
