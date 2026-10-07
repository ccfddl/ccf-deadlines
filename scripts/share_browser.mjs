// Shared, diagnostic browser startup for offline share-image builds.
import { spawn, spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';

export async function waitForDevTools(browser, readPort, {timeoutMs = 20000, stderr = () => ''} = {}) {
  let spawnError;
  const onError = error => { spawnError = error; };
  browser.on('error', onError);
  const deadline = Date.now() + timeoutMs;
  try {
    while (true) {
      if (spawnError || browser.exitCode !== null || browser.signalCode !== null) {
        throw new Error(`Browser exited before DevTools: ${spawnError?.message || `code=${browser.exitCode} signal=${browser.signalCode}`}`);
      }
      const port = readPort();
      if (/^\d+$/.test(port || '')) return port;
      if (Date.now() >= deadline) throw new Error(`Browser startup timed out after ${timeoutMs}ms`);
      await delay(Math.min(50, Math.max(1, deadline - Date.now())));
    }
  } catch (error) {
    throw new Error(`${error.message}\nBrowser stderr (last 8 KiB):\n${stderr().slice(-8192) || '(empty)'}`);
  } finally {
    browser.removeListener('error', onError);
  }
}

export async function stopBrowser(browser) {
  if (browser.exitCode !== null || browser.signalCode !== null) return;
  let onExit;
  const exited = new Promise(done => { onExit = done; browser.once('exit', onExit); });
  browser.kill();
  await Promise.race([exited, delay(2000, undefined, {ref: false})]);
  if (browser.exitCode === null && browser.signalCode === null) browser.kill('SIGKILL');
  browser.removeListener('exit', onExit);
}

export async function launchShareBrowser() {
  const chrome = process.env.CHROME_BINARY ?? process.env.CHROME_BIN ?? [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome', '/usr/bin/chromium',
  ].find(existsSync);
  if (!chrome) throw new Error('Share cards require Chrome/Chromium; set CHROME_BINARY if needed');
  const version = spawnSync(chrome, ['--version'], {encoding: 'utf8', timeout: 5000});
  if (version.error || version.status !== 0) {
    throw new Error(`Cannot execute browser ${chrome}: ${version.error?.message || version.stderr || `exit ${version.status}`}`);
  }
  console.error(`Share-card browser: ${chrome} (${version.stdout.trim()})`);
  const profile = mkdtempSync(join(tmpdir(), 'ccfddl-share-'));
  const browser = spawn(chrome, ['--headless=new', '--disable-extensions', '--no-first-run',
    '--no-default-browser-check', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
    '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'],
  {stdio: ['ignore', 'ignore', 'pipe']});
  let stderr = '';
  browser.stderr.on('data', chunk => { stderr = (stderr + chunk).slice(-8192); });
  const cleanup = async () => {
    await stopBrowser(browser);
    rmSync(profile, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
  };
  try {
    const file = join(profile, 'DevToolsActivePort');
    const port = await waitForDevTools(browser, () => existsSync(file) ? readFileSync(file, 'utf8').split('\n')[0] : '', {stderr: () => stderr});
    return {browser, port, cleanup};
  } catch (error) {
    await cleanup();
    throw error;
  }
}
