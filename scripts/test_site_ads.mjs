import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { runInNewContext } from 'node:vm';

const source = readFileSync(new URL('../public/site-ads.js', import.meta.url), 'utf8');

function page({ loading = true, content = false, idle = true, readyState = 'complete', selector = '[data-ad-content-ready="true"]' } = {}) {
  const scripts = [];
  const frames = [];
  const tasks = [];
  const listeners = new Map();
  let notify;
  let disconnected = false;
  const document = {
    readyState, documentElement: {},
    currentScript: { getAttribute: () => selector },
    getElementById: () => loading ? {} : null,
    querySelector: value => value.startsWith('script[') ? scripts[0] : content ? {} : null,
    createElement: tag => { assert.equal(tag, 'script'); return {}; },
    head: { appendChild: script => scripts.push(script) },
    addEventListener: (name, callback) => listeners.set(name, callback),
  };
  const window = {
    requestAnimationFrame: callback => frames.push(callback),
    setTimeout: callback => tasks.push(callback),
    ...(idle ? { requestIdleCallback: callback => tasks.push(callback) } : {}),
  };
  class MutationObserver {
    constructor(callback) { notify = callback; }
    observe() {}
    disconnect() { disconnected = true; }
  }
  const context = { document, window, MutationObserver };
  runInNewContext(source, context);
  return {
    scripts, frames, tasks,
    update(next) { loading = next.loading ?? loading; content = next.content ?? content; notify?.(); },
    ready() { document.readyState = 'interactive'; listeners.get('DOMContentLoaded')?.(); },
    paint() { frames.splice(0).forEach(callback => callback()); },
    idle() { tasks.splice(0).forEach(callback => callback()); },
    rerun() { runInNewContext(source, context); },
    get disconnected() { return disconnected; },
  };
}

test('an app mount without conference content does not request ads', () => {
  const app = page();
  app.update({ loading: false });
  assert.equal(app.frames.length, 0);
  assert.equal(app.scripts.length, 0);
  app.update({ content: true });
  app.update({ content: true });
  assert.equal(app.frames.length, 1);
  assert.equal(app.scripts.length, 0);
  app.paint();
  assert.equal(app.scripts.length, 0);
  app.idle();
  assert.equal(app.scripts.length, 1);
  assert.match(app.scripts[0].src, /client=ca-pub-2114972416819347$/);
  assert.equal(app.scripts[0].crossOrigin, 'anonymous');
  assert.equal(app.scripts[0].async, true);
  assert.equal(app.disconnected, true);
});

test('the original loading panel blocks ads even when a content marker exists', () => {
  const app = page({ content: true });
  assert.equal(app.frames.length, 0);
  app.update({ loading: false });
  app.paint(); app.idle();
  assert.equal(app.scripts.length, 1);
});

test('content disappearing during the idle wait cancels that request and allows retry', () => {
  const app = page({ loading: false, content: true });
  app.paint();
  app.update({ content: false });
  app.idle();
  assert.equal(app.scripts.length, 0);
  assert.equal(app.disconnected, false);
  app.update({ content: true });
  app.paint(); app.idle();
  assert.equal(app.scripts.length, 1);
});

test('duplicate loader executions do not duplicate the Google script', () => {
  const app = page({ loading: false, content: true });
  app.paint(); app.idle();
  app.rerun();
  app.paint(); app.idle();
  assert.equal(app.scripts.length, 1);
});

test('static detail content waits for DOM readiness and the next paint', () => {
  const detail = page({ loading: false, content: true, readyState: 'loading', selector: '.detail-card' });
  assert.equal(detail.frames.length, 0);
  detail.ready();
  assert.equal(detail.frames.length, 1);
  detail.paint(); detail.idle();
  assert.equal(detail.scripts.length, 1);
});

test('browsers without requestIdleCallback still wait for content and paint', () => {
  const app = page({ loading: false, content: true, idle: false });
  assert.equal(app.scripts.length, 0);
  app.paint();
  assert.equal(app.scripts.length, 0);
  app.idle();
  assert.equal(app.scripts.length, 1);
});
