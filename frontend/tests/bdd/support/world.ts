/**
 * HangmanWorld — custom World shared across every scenario's steps.
 *
 * Each scenario gets a fresh context+page+apiRequest (see hooks.ts), so this
 * is where per-scenario state — the last API response, the last parsed body —
 * lives. Lifecycle rules: `browser` is shared (BeforeAll/AfterAll);
 * `context`, `page`, and `apiRequest` are per-scenario (Before/After).
 */
import { World, type IWorldOptions, setWorldConstructor } from '@cucumber/cucumber';
import type { Browser, BrowserContext, Page, APIRequestContext, APIResponse } from 'playwright';

export class HangmanWorld extends World {
  public browser!: Browser;
  public context!: BrowserContext;
  public page!: Page;
  public apiRequest!: APIRequestContext;

  public lastApiResponse: APIResponse | null = null;
  public lastApiBody: unknown = null;

  public dialogCount = 0;

  get backendUrl(): string {
    const port = process.env.HANGMAN_BACKEND_PORT ?? '8000';
    return `http://localhost:${port}`;
  }

  get frontendUrl(): string {
    const port = process.env.HANGMAN_FRONTEND_PORT ?? '3000';
    return `http://localhost:${port}`;
  }

  constructor(options: IWorldOptions) {
    super(options);
  }
}

setWorldConstructor(HangmanWorld);
