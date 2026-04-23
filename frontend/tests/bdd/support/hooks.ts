/**
 * Browser lifecycle + per-scenario isolation for the BDD suite.
 *
 * Lifecycle choice (design §3, browser-lifecycle A):
 *   - Shared browser (BeforeAll/AfterAll)            — fast
 *   - Per-scenario context+page (Before/After)       — isolates cookies
 *
 * BeforeAll pings both servers in parallel once so the suite fails fast with
 * a clear "did you run make backend-test / make frontend?" message instead of
 * a cryptic ECONNREFUSED deep inside a scenario. Once per run is enough —
 * the servers don't come and go mid-suite.
 */
import { BeforeAll, Before, After, AfterAll, Status } from '@cucumber/cucumber';
import { chromium, request, type Browser } from 'playwright';
import type { HangmanWorld } from './world';

let sharedBrowser: Browser;

interface ServiceProbe {
  probeUrl: () => string;
  makeTarget: string;
  portEnvName: 'HANGMAN_BACKEND_PORT' | 'HANGMAN_FRONTEND_PORT';
}

const SERVICES: Record<'Backend' | 'Frontend', ServiceProbe> = {
  Backend: {
    probeUrl: () =>
      `http://localhost:${process.env.HANGMAN_BACKEND_PORT ?? '8000'}/api/v1/categories`,
    makeTarget: 'make backend-test',
    portEnvName: 'HANGMAN_BACKEND_PORT',
  },
  Frontend: {
    probeUrl: () => `http://localhost:${process.env.HANGMAN_FRONTEND_PORT ?? '3000'}`,
    makeTarget: 'make frontend',
    portEnvName: 'HANGMAN_FRONTEND_PORT',
  },
};

async function assertReachable(name: string, probe: ServiceProbe): Promise<void> {
  const url = probe.probeUrl();
  try {
    // The frontend root may return 404 for some SPA configurations but the
    // TCP connect and HTTP response are both fine — that's reachable enough
    // for our purposes. We only fail on thrown errors (ECONNREFUSED etc).
    await fetch(url);
  } catch (err) {
    const portHint = process.env[probe.portEnvName]
      ? ` (${probe.portEnvName}=${process.env[probe.portEnvName]})`
      : '';
    throw new Error(
      `${name} not reachable at ${url} — did you run ` +
        `\`${probe.makeTarget}\`${portHint}? Underlying error: ${(err as Error).message}`,
    );
  }
}

BeforeAll(async function () {
  // Fail-fast BEFORE launching chromium; cheaper for CI if servers are down.
  // Probes run in parallel — error messages carry the service name so a
  // Promise.all rejection still identifies which service is down.
  await Promise.all(Object.entries(SERVICES).map(([name, probe]) => assertReachable(name, probe)));
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
  this.rememberedSessionValue = null;
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
