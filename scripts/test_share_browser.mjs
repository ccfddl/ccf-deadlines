import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import test from 'node:test';
import { waitForDevTools, stopBrowser } from './share_browser.mjs';

const child = () => Object.assign(new EventEmitter(), {exitCode: null, signalCode: null});

test('waits for a complete DevTools port file', async () => {
  const browser = child(); let calls = 0;
  const port = await waitForDevTools(browser, () => ++calls > 1 ? '9222' : '', {timeoutMs: 200});
  assert.equal(port, '9222');
  assert.equal(browser.listenerCount('error'), 0);
});

test('reports exit code and captured stderr immediately', async () => {
  const browser = child(); browser.exitCode = 127;
  await assert.rejects(waitForDevTools(browser, () => '', {stderr: () => 'missing shared library'}),
    /code=127.*\nBrowser stderr.*\nmissing shared library/);
});

test('reports spawn error instead of unhandled error event', async () => {
  const browser = child();
  const waiting = waitForDevTools(browser, () => '', {timeoutMs: 200});
  browser.emit('error', new Error('ENOENT: missing browser'));
  await assert.rejects(waiting, /ENOENT: missing browser/);
});

test('reports timeout with bounded stderr, no silent retry', async () => {
  const browser = child();
  await assert.rejects(waitForDevTools(browser, () => '', {timeoutMs: 2, stderr: () => 'x'.repeat(9000) + ' diagnostic'}), error => {
    assert.match(error.message, /startup timed out/);
    assert.match(error.message, /diagnostic$/);
    assert.ok(error.message.length < 8400);
    return true;
  });
});

test('cleanup returns when process was already terminated by a signal', async () => {
  const browser = child(); browser.signalCode = 'SIGTERM';
  browser.kill = () => assert.fail('already-exited browser must not be killed again');
  await stopBrowser(browser);
});

test('cleanup waits for a running browser to exit', async () => {
  const browser = child();
  browser.kill = () => { browser.signalCode = 'SIGTERM'; browser.emit('exit'); };
  await stopBrowser(browser);
  assert.equal(browser.listenerCount('exit'), 0);
});
