// Render all conference cards in one Chromium session, using the actual site's
// generated stylesheet. No bundled font, image service, or npm dependencies.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve, sep } from 'node:path';
import { launchShareBrowser } from './share_browser.mjs';

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
    const encoded = await evaluate(`drawShareCard(${JSON.stringify(card)})`);
    mkdirSync(dirname(targetPath), {recursive: true});
    writeFileSync(targetPath, Buffer.from(encoded, 'base64'));
  }
} finally {
  for (const waiting of pending.values()) clearTimeout(waiting.timer);
  socket?.close();
  await cleanup();
}

function drawShareCard(card) {
  const canvas = document.createElement('canvas'); canvas.width = 1200; canvas.height = 630;
  const ctx = canvas.getContext('2d', {alpha: false});
  ctx.fillStyle = window.shareBackground; ctx.fillRect(0, 0, 1200, 630);
  ctx.textBaseline = 'top';
  function label(value, x, y, size, color = window.shareInk, width = 1040, limit = 1) {
    ctx.font = `${size}px ${window.shareFont}`; ctx.fillStyle = color;
    let remaining = String(value || '').replace(/\s+/g, ' ').trim();
    for (let row = 0; remaining && row < limit; row++) {
      let end = remaining.length;
      while (end > 1 && ctx.measureText(remaining.slice(0, end)).width > width) end--;
      if (end < remaining.length && row + 1 < limit) {
        const space = remaining.lastIndexOf(' ', end); if (space > 0) end = space;
      }
      let line = remaining.slice(0, end).trimEnd(); remaining = remaining.slice(end).trimStart();
      if (remaining && row + 1 === limit) {
        while (line && ctx.measureText(line + '…').width > width) line = line.slice(0, -1);
        line += '…';
      }
      ctx.fillText(line, x, y + row * (size + 8));
    }
  }
  const muted = '#67727e', accent = '#d9554f';
  label('CCFDDL Open', 64, 42, 28);
  ctx.font = `28px ${window.shareFont}`;
  label('Deadlines', 64 + ctx.measureText('CCFDDL Open ').width, 42, 28, accent);
  ctx.strokeStyle = '#e5ded6'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(64, 91); ctx.lineTo(1136, 91); ctx.stroke();
  ctx.fillStyle = '#fffdfa'; ctx.beginPath(); ctx.roundRect(48, 119, 1104, 421, 16); ctx.fill(); ctx.stroke();
  label(card.category, 80, 146, 23, muted);
  label(card.title, 80, 192, 62);
  label(card.description, 80, 272, 28, muted, 1040, 2);
  label('CONFERENCE DATES', 80, 371, 17, muted);
  label(card.date || 'Dates to be announced', 80, 403, 27);
  label(card.place || 'Location to be announced', 80, 457, 25, muted);
  label('Conference deadlines and details', 64, 568, 23, muted);
  label('ccfddl.com', 949, 565, 27, accent, 220);
  return canvas.toDataURL('image/png').split(',')[1];
}
