// Render all conference cards in one Chromium session, using the actual site's
// generated stylesheet. No bundled font, image service, or npm dependencies.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve, sep } from 'node:path';
import { launchShareBrowser } from './share_browser.mjs';
import { drawShareCard } from './share_card_canvas.mjs';

const {cards, css} = JSON.parse(readFileSync(0, 'utf8'));
const output = resolve(process.argv[2]);
const {port, cleanup} = await launchShareBrowser();
let socket, nextId = 0;
const pending = new Map();
function command(method, params = {}) {
  return new Promise((done, fail) => {
    const id = ++nextId;
    const timer = setTimeout(() => { pending.delete(id); fail(new Error(`Timed out: ${method}`)); }, 30000);
    pending.set(id, {done, fail, timer});
    socket.send(JSON.stringify({id, method, params}));
  });
}
async function evaluate(expression) {
  const result = await command('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
try {
  const targets = await fetch(`http://127.0.0.1:${port}/json/list`).then(r => r.json());
  const target = targets.find(t => t.type === 'page');
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((done, fail) => {
    socket.addEventListener('open', done, {once: true});
    socket.addEventListener('error', fail, {once: true});
  });
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data), waiting = pending.get(message.id);
    if (!waiting) return;
    pending.delete(message.id); clearTimeout(waiting.timer);
    if (message.error) waiting.fail(new Error(message.error.message));
    else waiting.done(message.result);
  });
  // CSS and conference text are data, never interpolated into executable HTML.
  await evaluate(`(() => {
    const style = document.createElement('style'); style.textContent = ${JSON.stringify(css)};
    document.head.append(style); document.body.className = 'detail-page';
    const home = document.createElement('div'); home.className = 'home'; document.body.append(home);
    window.shareFont = getComputedStyle(home).fontFamily;
    window.shareInk = getComputedStyle(home).color;
    window.shareBackground = getComputedStyle(document.body).backgroundColor;
  })()`);
  await evaluate(`document.fonts.ready.then(() => true)`);
  await evaluate(`window.drawShareCard = ${drawShareCard.toString()}`);
  for (const card of cards) {
    const targetPath = resolve(output, '.' + card.path, 'share.png');
    if (!targetPath.startsWith(output + sep)) throw new Error('Invalid share-card path');
    const {encoded, report} = await evaluate(`drawShareCard(${JSON.stringify(card)})`);
    if (report.renderedDeadlines !== (card.deadlines || []).length) throw new Error(`Incomplete card: ${card.path}`);
    if (Buffer.byteLength(encoded, 'base64') >= 5_000_000) throw new Error(`Share image exceeds 5 MB: ${card.path}`);
    mkdirSync(dirname(targetPath), {recursive: true});
    writeFileSync(targetPath, Buffer.from(encoded, 'base64'));
  }
} finally {
  for (const waiting of pending.values()) clearTimeout(waiting.timer);
  socket?.close();
  await cleanup();
}
