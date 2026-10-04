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
let fixture = 'wide';
const testConferences = () => {
  const conferences = [{
    title: 'TIMELINETEST', description: 'Timeline interaction regression', sub: 'AI',
    rank: {ccf: 'A'}, dblp: 'test',
    confs: [{year: 2027, id: 'timelinetest27', link: 'https://example.org',
      timeline: [fixture === 'keyboard'
        ? {abstract_deadline: '2027-06-07 19:59:00', deadline: '2027-06-13 19:59:00', rebuttal_deadline: '2027-06-18 19:59:00', decision_deadline: '2027-06-19 19:59:00'}
        : fixture === 'close'
        ? {abstract_deadline: '2026-11-05 19:59:00', deadline: testDeadline, rebuttal_deadline: '2026-11-17 19:59:00', decision_deadline: '2026-11-18 19:59:00'}
        : {abstract_deadline: '2026-10-05 19:59:00', deadline: testDeadline, rebuttal_deadline: '2027-01-15 19:59:00', decision_deadline: '2027-02-11 19:59:00'}], timezone: 'UTC',
      date: 'June 20-25, 2027', opening: '2027-06-20 08:00:00', place: 'Virtual'},
    ],
  }];
  if (fixture === 'multiple') {
    conferences.push({...conferences[0], title: 'TIMELINETESTOTHER',
      confs: conferences[0].confs.map(edition => ({...edition, id: 'timelinetestother27'}))});
  }
  return conferences;
};
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

async function pressKey(key, code, windowsVirtualKeyCode) {
  await command('Input.dispatchKeyEvent', {type:'keyDown',key,code,windowsVirtualKeyCode});
  await command('Input.dispatchKeyEvent', {type:'keyUp',key,code,windowsVirtualKeyCode});
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
  const bounds = async () => {
    const result = await evaluate(`(() => {
    const container = document.querySelector('.conference-detail-timeline .all_line');
    const preview = container.querySelector('.timeline-preview');
    if (!preview) return null;
    const box = preview.getBoundingClientRect(), outer = container.getBoundingClientRect();
    return {text: preview.textContent.trim(), left:box.left, right:box.right, width:box.width,
      containerLeft:outer.left, containerRight:outer.right,
      clipped:preview.scrollWidth > preview.clientWidth,
      now:getComputedStyle(container.querySelector('.sel_dot'), '::after').visibility,
      dot:getComputedStyle(container.querySelector('.sel_dot')).visibility,
      align:getComputedStyle(container.querySelector('.timeline-preview-slot')).justifyContent};
    })()`);
    if (result) assert.equal(result.dot, 'visible', 'NOW dot remains visible during interaction');
    return result;
  };
  for (fixture of ['wide', 'close']) {
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
        assert.equal(await evaluate("getComputedStyle(document.querySelector('.conference-detail-timeline .sel_dot'), '::after').visibility"), 'visible');
        // The visible NOW label resolves to a hit-testable wrapper with its exact time.
        const reference = await evaluate(`(() => {
          const dot = document.querySelector('.conference-detail-timeline .sel_dot');
          const box = dot.getBoundingClientRect();
          const label = getComputedStyle(dot, '::after');
          const point = {x:box.left+box.width/2,y:box.top-parseFloat(label.bottom)+2};
          const target = document.elementFromPoint(point.x, point.y);
          return {point, title:target?.closest('[title]')?.title,
            accessible:dot.closest('.all_line').getAttribute('aria-label')};
        })()`);
        assert.equal(reference.title, 'Now: 2026-10-04 00:00:00');
        assert.equal(reference.accessible, reference.title);
        await command('Input.dispatchMouseEvent', {type:'mouseMoved',...reference.point});
        assert.equal(await bounds(), null, 'reference tooltip does not select a milestone');
        await command('Input.dispatchMouseEvent', {type:'mouseMoved',x:1,y:1});
        // Exercise native hit testing at every marker, including six-day and one-day gaps.
        for (const input of ['mouse', 'touch']) {
          await command('Emulation.setTouchEmulationEnabled', {enabled: input === 'touch'});
          for (let index=0; index<5; index++) {
            await command('Input.dispatchMouseEvent', {type:'mouseMoved',x:1,y:1});
            const marker = await evaluate(`(() => {
              const node = document.querySelectorAll('.conference-detail-timeline .timeline-event')[${index}];
              const box = node.nextElementSibling.getBoundingClientRect();
              const target = node.getBoundingClientRect();
              // Use the visible part of each marker that belongs to its bounded target.
              // Subpixel-spaced markers can share a visual centre pixel; never click
              // another marker's part of that shared glyph.
              const x = (Math.max(box.left, target.left) + Math.min(box.right, target.right)) / 2;
              const y = box.top + box.height / 2;
              return {point: {x,y}, label: node.getAttribute('aria-label'),
                hit: document.elementFromPoint(x,y)?.closest('.timeline-event') === node};
            })()`);
            assert.equal(marker.hit, true, `${fixture} ${mode} ${width} marker ${index} owns its visible hit area`);
            const activate = async () => {
              if (input === 'mouse') {
                await command('Input.dispatchMouseEvent', {type:'mouseMoved',...marker.point});
                await command('Input.dispatchMouseEvent', {type:'mousePressed',button:'left',clickCount:1,...marker.point});
                await command('Input.dispatchMouseEvent', {type:'mouseReleased',button:'left',clickCount:1,...marker.point});
              } else {
                await command('Input.dispatchTouchEvent', {type:'touchStart',touchPoints:[{...marker.point,radiusX:1,radiusY:1}]});
                await command('Input.dispatchTouchEvent', {type:'touchEnd',touchPoints:[]});
              }
            };
            await activate();
            await until(bounds, 'selected preview');
            let preview=await bounds();
            if (input === 'mouse' || fixture === 'wide' || index === 4) {
              assert.equal(preview.text.replace(/\s+/g, ' '), marker.label, 'native marker selection');
            }
            if (fixture === 'close' && index < 4) {
              // Mobile browsers can redirect tiny taps. The nearby picker must offer
              // a full-sized physical target for the exact intended milestone.
              const choice = await evaluate(`(() => {
                const node = [...document.querySelectorAll('.timeline-choice')].find(n => n.getAttribute('aria-label') === ${JSON.stringify(marker.label)});
                if (!node) return null;
                const box = node.getBoundingClientRect();
                return {x:box.left+box.width/2,y:box.top+box.height/2};
              })()`);
              assert.ok(choice, 'nearby milestone choice exists');
              if (input === 'touch') {
                await command('Input.dispatchTouchEvent', {type:'touchStart',touchPoints:[choice]});
                await command('Input.dispatchTouchEvent', {type:'touchEnd',touchPoints:[]});
              } else {
                await command('Input.dispatchMouseEvent', {type:'mouseMoved',...choice});
                await command('Input.dispatchMouseEvent', {type:'mousePressed',button:'left',clickCount:1,...choice});
                await command('Input.dispatchMouseEvent', {type:'mouseReleased',button:'left',clickCount:1,...choice});
              }
              await until(async () => (await bounds())?.text.replace(/\s+/g, ' ') === marker.label, 'intended nearby choice');
              preview=await bounds();
            }
            assert.equal(preview.text.replace(/\s+/g, ' '), marker.label, `${fixture} ${mode} ${width} ${input} marker ${index}`);
            assert.equal(await evaluate(`document.querySelectorAll('.conference-detail-timeline .timeline-event')[${index}].getAttribute('aria-pressed')`), 'true');
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
            if (fixture === 'wide') {
              await activate();
            } else {
              const outside = await evaluate(`(() => {
                const box = document.querySelector('.conference-detail-description').getBoundingClientRect();
                return {x:box.left+10,y:box.top+box.height/2};
              })()`);
              if (input === 'touch') {
                await command('Input.dispatchTouchEvent', {type:'touchStart',touchPoints:[outside]});
                await command('Input.dispatchTouchEvent', {type:'touchEnd',touchPoints:[]});
              } else {
                await command('Input.dispatchMouseEvent', {type:'mouseMoved',...outside});
                await command('Input.dispatchMouseEvent', {type:'mousePressed',button:'left',clickCount:1,...outside});
                await command('Input.dispatchMouseEvent', {type:'mouseReleased',button:'left',clickCount:1,...outside});
              }
            }
            await until(() => evaluate("!document.querySelector('.conference-detail-timeline .timeline-preview')"), 'physical dismissal');
            assert.equal(await evaluate("getComputedStyle(document.querySelector('.conference-detail-timeline .sel_dot'), '::after').visibility"), 'visible');
          }
        }
        await command('Emulation.setTouchEmulationEnabled', {enabled:false});
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
          const box = document.querySelector('.conference-detail-timeline .timeline-marker').getBoundingClientRect();
          return {x: box.left+box.width/2, y:box.top+box.height/2};
        })()`);
        await command('Input.dispatchMouseEvent',{type:'mouseMoved',...point});
        await until(bounds,'hover preview');
        assert.equal((await bounds()).now,'hidden');
        await command('Input.dispatchMouseEvent',{type:'mouseMoved',x:1,y:1});
        await until(() => evaluate("!document.querySelector('.conference-detail-timeline .timeline-preview')"),'hover dismissal');
        assert.equal(await evaluate("getComputedStyle(document.querySelector('.conference-detail-timeline .sel_dot'), '::after').visibility"),'visible');
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
        console.log('Physical pointer/touch selection, dismissal and label bounds passed:',fixture,mode,width);
      }
      await command('Page.removeScriptToEvaluateOnNewDocument',{identifier:preferences.identifier});
    }
  }
  // Keep Opening next to Decisions so native Tab can enter the nearby picker
  // from the final marker, without a mouse-selected fallback holding it open.
  fixture = 'keyboard';
  const keyboardPreferences = await command('Page.addScriptToEvaluateOnNewDocument', {source: `
    localStorage.setItem('conference_view', 'cards');
    localStorage.setItem('conference_search', 'TIMELINETEST');
  `});
  for (const width of [1280, 390, 320]) {
    await command('Emulation.setDeviceMetricsOverride', {width,height:1100,deviceScaleFactor:1,mobile:false});
    await command('Page.navigate', {url:`http://127.0.0.1:${server.address().port}/?filters=all`});
    await until(present, 'keyboard fixture loaded');
    await evaluate("document.querySelector('.conf-title').click()");
    await until(() => evaluate("document.querySelectorAll('.conference-detail-timeline .timeline-event').length === 5"), 'keyboard timeline buttons');
    await command('Input.dispatchMouseEvent', {type:'mouseMoved',x:1,y:1});
    await evaluate("document.querySelectorAll('.conference-detail-timeline .timeline-event')[4].focus()");
    await until(() => evaluate("document.querySelectorAll('.conference-detail-timeline .timeline-choice').length >= 2"), 'focus-only nearby choices');
    assert.equal(await evaluate("document.querySelectorAll('.conference-detail-timeline .timeline-event[aria-pressed=true]').length"), 0, 'picker starts with no clicked selection');
    const choices = await evaluate("[...document.querySelectorAll('.conference-detail-timeline .timeline-choice')].map(node => node.getAttribute('aria-label'))");
    for (const label of choices.slice(0,2)) {
      await pressKey('Tab', 'Tab', 9);
      await until(async () => (await bounds())?.text.replace(/\s+/g, ' ') === label, 'Tab focus previews the nearby choice');
      assert.equal(await evaluate(`(() => {
        const choice = document.activeElement;
        return choice?.matches('.conference-detail-timeline .timeline-choice')
          && choice.getAttribute('aria-label') === ${JSON.stringify(label)};
      })()`), true, 'nearby choice retains actual keyboard focus');
    }
    await pressKey('Enter', 'Enter', 13);
    await until(() => evaluate("document.querySelectorAll('.conference-detail-timeline .timeline-event[aria-pressed=true]').length === 1"), 'keyboard nearby choice selection');
    assert.equal((await bounds()).text.replace(/\s+/g, ' '), choices[1]);
    await pressKey('Escape', 'Escape', 27);
    await until(() => evaluate("!document.querySelector('.conference-detail-timeline .timeline-preview')"), 'nearby choice Escape dismissal');
    assert.equal(await evaluate("Boolean(document.querySelector('.conference-detail-title'))"), true);
    // Reopen from focus alone, then Tab through all choices and out of the
    // timeline. Outside focus must clear the final preview and restore NOW.
    await evaluate("document.querySelectorAll('.conference-detail-timeline .timeline-event')[4].focus()");
    for (let tab=0;tab<choices.length+1;tab++) await pressKey('Tab', 'Tab', 9);
    assert.equal(await evaluate("document.querySelector('.conference-detail-timeline .time_con').contains(document.activeElement)"), false, 'Tab leaves the nearby picker');
    await until(() => evaluate("!document.querySelector('.conference-detail-timeline .timeline-preview')"), 'Tab outside nearby choices');
    assert.equal(await evaluate("document.querySelectorAll('.conference-detail-timeline .timeline-event[aria-pressed=true]').length"), 0);
    assert.equal(await evaluate("getComputedStyle(document.querySelector('.conference-detail-timeline .sel_dot'), '::after').visibility"), 'visible');
    console.log('Focus-only nearby picker Tab/Enter/Escape and outside dismissal passed:',width);
  }
  await command('Page.removeScriptToEvaluateOnNewDocument', {identifier:keyboardPreferences.identifier});
  // Clicks stopped by one row must still dismiss a selection in another row.
  fixture = 'multiple';
  const multiPreferences = await command('Page.addScriptToEvaluateOnNewDocument', {source: `
    localStorage.setItem('conference_view', 'list');
    localStorage.setItem('conference_search', 'TIMELINETEST');
  `});
  for (const width of [1280, 390, 320]) {
    await command('Emulation.setDeviceMetricsOverride', {width,height:1100,deviceScaleFactor:1,mobile:false});
    for (const input of ['mouse', 'touch']) {
      await command('Emulation.setTouchEmulationEnabled', {enabled:input === 'touch'});
      await command('Page.navigate', {url:`http://127.0.0.1:${server.address().port}/?filters=all`});
      await until(() => evaluate("document.querySelectorAll('.time_con').length === 2"), 'two inline timelines');
      const clickMarker = async (index) => {
        const point = await evaluate(`(() => {
          const timeline = document.querySelectorAll('.time_con')[${index}];
          timeline.scrollIntoView({block:'center'});
          const box = timeline.querySelector('.timeline-event').getBoundingClientRect();
          return {x:box.left+box.width/2,y:box.top+box.height/2};
        })()`);
        if (input === 'touch') {
          await command('Input.dispatchTouchEvent', {type:'touchStart',touchPoints:[point]});
          await command('Input.dispatchTouchEvent', {type:'touchEnd',touchPoints:[]});
        } else {
          await command('Input.dispatchMouseEvent', {type:'mouseMoved',...point});
          await command('Input.dispatchMouseEvent', {type:'mousePressed',button:'left',clickCount:1,...point});
          await command('Input.dispatchMouseEvent', {type:'mouseReleased',button:'left',clickCount:1,...point});
        }
      };
      for (const index of [0,1,0]) {
        await clickMarker(index);
        await until(() => evaluate(`(() => {
          const timelines=[...document.querySelectorAll('.time_con')];
          return timelines.every((node,i) => Boolean(node.querySelector('.timeline-preview')) === (i === ${index}));
        })()`), 'only the clicked timeline remains selected');
        assert.equal(await evaluate("document.querySelectorAll('.time_con.is-interacting').length"), 1);
        assert.equal(await evaluate("document.querySelectorAll('.conference-detail-dialog').length"), 0, 'marker click must not open the row dialog');
        assert.equal(await evaluate("[...document.querySelectorAll('.time_con .sel_dot')].every(dot => getComputedStyle(dot).visibility === 'visible')"), true);
      }
      await clickMarker(0);
      await until(() => evaluate("document.querySelectorAll('.time_con.is-interacting').length === 0"), 'selected marker toggles off');
      await command('Input.dispatchMouseEvent', {type:'mouseMoved',x:1,y:1});
      console.log('Cross-timeline physical selection and same-marker dismissal passed:',width,input);
    }
    await command('Emulation.setTouchEmulationEnabled', {enabled:false});
    await evaluate("document.querySelectorAll('.time_con')[0].querySelector('.timeline-event').focus()");
    for (let tab=0;tab<30;tab++) {
      if (await evaluate("document.activeElement?.closest('.time_con') === document.querySelectorAll('.time_con')[1]")) break;
      await command('Input.dispatchKeyEvent', {type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
      await command('Input.dispatchKeyEvent', {type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
    }
    assert.equal(await evaluate("document.activeElement?.closest('.time_con') === document.querySelectorAll('.time_con')[1]"), true);
    assert.equal(await evaluate("Boolean(document.querySelectorAll('.time_con')[0].querySelector('.timeline-preview'))"), false, 'keyboard focus dismisses the other timeline');
    // Leaving a keyboard-selected timeline must also clear its sticky preview.
    await evaluate("document.querySelectorAll('.time_con')[1].querySelectorAll('.timeline-event')[4].focus()");
    await pressKey('Enter', 'Enter', 13);
    await until(() => evaluate("document.querySelectorAll('.time_con')[1].querySelectorAll('.timeline-event[aria-pressed=true]').length === 1"), 'keyboard sticky selection');
    await pressKey('Tab', 'Tab', 9);
    assert.equal(await evaluate("document.querySelectorAll('.time_con')[1].contains(document.activeElement)"), false, 'Tab leaves the last timeline');
    await until(() => evaluate("!document.querySelectorAll('.time_con')[1].querySelector('.timeline-preview')"), 'Tab outside clears sticky preview');
    assert.equal(await evaluate("document.querySelectorAll('.time_con')[1].querySelectorAll('.timeline-event[aria-pressed=true]').length"), 0);
    assert.equal(await evaluate("getComputedStyle(document.querySelectorAll('.time_con')[1].querySelector('.sel_dot'), '::after').visibility"), 'visible');
    // Custom reference times expose BASE through the same hit-testable wrapper.
    await evaluate(`(() => {
      const input=document.querySelector('#base-time-input');
      input.value='2026-10-04T00:00:00';
      input.dispatchEvent(new Event('change',{bubbles:true}));
    })()`);
    await until(() => evaluate("document.querySelectorAll('.time_con .sel_dot[data-label=BASE]').length === 2"), 'custom reference applied');
    await evaluate("document.querySelector('.conf-title').click()");
    await until(() => evaluate("Boolean(document.querySelector('.conference-detail-timeline .sel_dot[data-label=BASE]'))"), 'BASE in dialog');
    const base = await evaluate(`(() => {
      const dot=document.querySelector('.conference-detail-timeline .sel_dot');
      dot.scrollIntoView({block:'center'});
      const box=dot.getBoundingClientRect();
      const label=getComputedStyle(dot,'::after');
      const point={x:box.left+box.width/2,y:box.top-parseFloat(label.bottom)+2};
      return {point,title:document.elementFromPoint(point.x,point.y)?.closest('[title]')?.title,
        accessible:dot.closest('.all_line').getAttribute('aria-label')};
    })()`);
    assert.equal(base.title, 'Base: 2026-10-04 00:00:00');
    assert.equal(base.accessible, base.title);
    await command('Input.dispatchMouseEvent', {type:'mouseMoved',...base.point});
    assert.equal(await bounds(), null);
    console.log('Keyboard switching and native BASE tooltip target passed:',width);
  }
  await command('Page.removeScriptToEvaluateOnNewDocument', {identifier:multiPreferences.identifier});
  assert.deepEqual(errors, []);
  console.log('Timeline labels stay visible and NOW text hides during interaction while its dot stays visible');
} finally {
  socket?.close();
  browser.kill();
  await new Promise(done => browser.once('exit', done));
  server.closeAllConnections();
  await new Promise(done => server.close(done));
  rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}
