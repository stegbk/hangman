/**
 * Browser lifecycle + per-scenario isolation for the BDD suite.
 *
 * Lifecycle choice (design §3, browser-lifecycle A):
 *   - Shared browser (BeforeAll/AfterAll)            — fast
 *   - Per-scenario context+page (Before/After)       — isolates cookies
 *
 * BeforeAll pings both servers once so the suite fails fast with a clear
 * "did you run make backend-test / make frontend?" message instead of a
 * cryptic ECONNREFUSED deep inside a scenario. Once per run is enough —
 * the servers don't come and go mid-suite.
 */
import { BeforeAll, Before, After, AfterAll, Status } from '@cucumber/cucumber';
import { chromium, request, type Browser } from 'playwright';
import type { HangmanWorld } from './world';

let sharedBrowser: Browser;

function backendUrl(): string {
  return `http://localhost:${process.env.HANGMAN_BACKEND_PORT ?? '8000'}`;
}

function frontendUrl(): string {
  return `http://localhost:${process.env.HANGMAN_FRONTEND_PORT ?? '3000'}`;
}

async function assertReachable(
  label: 'backend' | 'frontend',
  url: string,
  makeTarget: 'make backend-test' | 'make frontend',
  portEnvName: 'HANGMAN_BACKEND_PORT' | 'HANGMAN_FRONTEND_PORT',
): Promise<void> {
  try {
    const res = await fetch(url);
    // The frontend root may return 404 for some SPA configurations but the
    // TCP connect and HTTP response are both fine — that's reachable enough
    // for our purposes. We only fail on thrown errors (ECONNREFUSED etc).
    void res;
  } catch (err) {
    const portHint = process.env[portEnvName]
      ? ` (${portEnvName}=${process.env[portEnvName]})`
      : '';
    throw new Error(
      `${label[0].toUpperCase() + label.slice(1)} not reachable at ${url} — did you run ` +
        `\`${makeTarget}\`${portHint}? Underlying error: ${(err as Error).message}`,
    );
  }
}

BeforeAll(async function () {
  // Fail-fast BEFORE launching chromium; cheaper for CI if servers are down.
  await assertReachable(
    'backend',
    `${backendUrl()}/api/v1/categories`,
    'make backend-test',
    'HANGMAN_BACKEND_PORT',
  );
  await assertReachable('frontend', frontendUrl(), 'make frontend', 'HANGMAN_FRONTEND_PORT');
  sharedBrowser = await chromium.launch();
});

AfterAll(async function () {
  await sharedBrowser?.close();
});

Before(async function (this: HangmanWorld) {
  this.browser = sharedBrowser;
  this.context = await sharedBrowser.newContext();
  this.page = await this.context.newPage();
  this.apiRequest = await request.newContext({ baseURL: this.backendUrl });
  this.lastApiResponse = null;
  this.lastApiBody = null;
  this.dialogCount = 0;
});

After(async function (this: HangmanWorld, { result }) {
  if (result?.status === Status.FAILED && this.page) {
    const buf = await this.page.screenshot();
    this.attach(buf, 'image/png');
  }
  await this.apiRequest?.dispose();
  await this.page?.close();
  await this.context?.close();
});
