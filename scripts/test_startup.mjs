import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { runInNewContext } from 'node:vm';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const source = html.match(/<script id="startup-recovery">([\s\S]*?)<\/script>/)[1];

function startup() {
  const listeners = new Map();
  const timers = new Map();
  const span = { textContent: 'Loading conference deadlines...' };
  const button = { hidden: true, addEventListener: (_, callback) => { button.click = callback; } };
  const loadingPanel = { querySelector: (tag) => tag === 'span' ? span : button };
  let panel = loadingPanel;
  let ready;
  let reloads = 0;
  const window = {
    location: { href: 'https://ccfddl.com/', origin: 'https://ccfddl.com', reload: () => reloads++ },
    addEventListener: (name, callback) => listeners.set(name, callback),
    removeEventListener: (name) => listeners.delete(name),
    setTimeout: (callback, delay) => { assert.equal(delay, 30000); timers.set(1, callback); return 1; },
    clearTimeout: (id) => timers.delete(id),
  };
  const document = {
    readyState: 'loading',
    getElementById: () => panel,
    addEventListener: (_, callback) => { ready = callback; },
  };
  runInNewContext(source, { window, document, URL });
  return {
    span, button, timers, listeners,
    ready() { document.readyState = 'interactive'; ready(); },
    emit(name, event = {}) { listeners.get(name)?.(event); },
    removePanel() { panel = null; },
    restorePanel() { panel = loadingPanel; },
    timeout() { const callback = timers.get(1); timers.delete(1); callback?.(); },
    get reloads() { return reloads; },
  };
}

test('failed app script exposes a retry button', () => {
  const app = startup();
  app.ready();
  app.emit('error', { target: { tagName: 'SCRIPT', src: 'https://ccfddl.com/app.js' } });
  assert.equal(app.button.hidden, false);
  assert.match(app.span.textContent, /Unable/);
  assert.equal(app.timers.size, 0);
  app.button.click();
  assert.equal(app.reloads, 1);
});

test('a failed module before DOM readiness still exposes retry', () => {
  const app = startup();
  app.removePanel();
  app.emit('unhandledrejection');
  app.restorePanel();
  app.ready();
  assert.equal(app.button.hidden, false);
});

test('slow startup exposes retry and still allows a later successful mount', () => {
  const app = startup();
  app.ready();
  app.timeout();
  assert.equal(app.button.hidden, false);
  app.removePanel();
  app.emit('TrunkApplicationStarted');
  assert.equal(app.listeners.has('error'), false);
  assert.equal(app.listeners.has('unhandledrejection'), false);
});

test('successful startup cancels the watchdog', () => {
  const app = startup();
  app.ready();
  app.removePanel();
  app.emit('TrunkApplicationStarted');
  assert.equal(app.timers.size, 0);
  app.timeout();
  assert.equal(app.button.hidden, true);
});

test('startup completed before DOM readiness does not start a watchdog', () => {
  const app = startup();
  app.removePanel();
  app.emit('TrunkApplicationStarted');
  app.ready();
  assert.equal(app.timers.size, 0);
});

test('watchdog starts before DOM readiness while application modules are pending', () => {
  const app = startup();
  app.emit('InitialLoadingReady');
  assert.equal(app.timers.size, 1);
  const originalTimer = app.timers.get(1);
  app.ready();
  assert.equal(app.timers.get(1), originalTimer);
  app.timeout();
  assert.equal(app.button.hidden, false);
  app.button.click();
  assert.equal(app.reloads, 1);
});

test('unrelated external scripts and extensions do not report startup failure', () => {
  const app = startup();
  app.ready();
  app.emit('error', { target: { tagName: 'SCRIPT', src: 'https://www.googletagmanager.com/gtag/js' } });
  app.emit('error', { filename: 'chrome-extension://test/injected.js', error: new Error('extension') });
  assert.equal(app.button.hidden, true);
  assert.equal(app.timers.size, 1);
});
