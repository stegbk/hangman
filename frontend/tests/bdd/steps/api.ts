/**
 * API-layer step definitions.
 *
 * Default HTTP client is page.request (shares the browser's cookie jar),
 * so `Given I start a new game ...` on the UI side and `When I request
 * /api/v1/...` on the API side see the same session cookie. The apiRequest
 * client (no shared cookies) is used only by the "fresh session" variants
 * that need cross-session isolation (games-current.feature scenario 3).
 */
import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';
import type { APIResponse } from 'playwright';
import type { HangmanWorld } from '../support/world';

async function storeResponse(world: HangmanWorld, res: APIResponse): Promise<void> {
  world.lastApiResponse = res;
  const text = await res.text();
  try {
    world.lastApiBody = text ? JSON.parse(text) : null;
  } catch {
    world.lastApiBody = text;
  }
}

function getPath(body: unknown, dotPath: string): unknown {
  const parts = dotPath.split('.');
  let cur: unknown = body;
  for (const part of parts) {
    if (cur === null || cur === undefined) return undefined;
    const idx = Number(part);
    if (Array.isArray(cur) && Number.isInteger(idx)) {
      cur = cur[idx];
    } else if (typeof cur === 'object') {
      cur = (cur as Record<string, unknown>)[part];
    } else {
      return undefined;
    }
  }
  return cur;
}

function currentGameId(world: HangmanWorld): string {
  const id = getPath(world.lastApiBody, 'id');
  // Backend Game.id is autoincrement int >= 1 (backend/src/hangman/models.py),
  // so 0 is never a real game id. Reject empty/zero/null/undefined loudly so
  // a malformed response body doesn't silently hit /games/0/guesses.
  if (typeof id === 'number' && Number.isFinite(id) && id > 0) {
    return String(id);
  }
  if (typeof id === 'string' && id.length > 0 && id !== '0') {
    return id;
  }
  throw new Error('No current game id in lastApiBody — start a game before calling this step.');
}

Given(
  'I start a new game with category {string} and difficulty {string}',
  async function (this: HangmanWorld, category: string, difficulty: string) {
    const res = await this.page.request.post(`${this.backendUrl}/api/v1/games`, {
      data: { category, difficulty },
    });
    await storeResponse(this, res);
    expect(res.status()).toBe(201);
  },
);

Given('I guess the letter {string}', async function (this: HangmanWorld, letter: string) {
  const id = currentGameId(this);
  const res = await this.page.request.post(`${this.backendUrl}/api/v1/games/${id}/guesses`, {
    data: { letter },
  });
  await storeResponse(this, res);
});

When('I request {string}', async function (this: HangmanWorld, path: string) {
  const res = await this.page.request.get(`${this.backendUrl}${path}`);
  await storeResponse(this, res);
});

When('I request {string} from a fresh session', async function (this: HangmanWorld, path: string) {
  // apiRequest has its own baseURL + no shared cookie jar, giving us
  // cross-session isolation for the 'different session' scenarios.
  const res = await this.apiRequest.get(path);
  await storeResponse(this, res);
});

When(
  'I POST to {string} with body:',
  async function (this: HangmanWorld, path: string, body: string) {
    const data = body.trim() ? JSON.parse(body) : {};
    const res = await this.page.request.post(`${this.backendUrl}${path}`, {
      data,
    });
    await storeResponse(this, res);
  },
);

When(
  "I POST to the current game's guesses endpoint with body:",
  async function (this: HangmanWorld, body: string) {
    const id = currentGameId(this);
    const data = body.trim() ? JSON.parse(body) : {};
    const res = await this.page.request.post(`${this.backendUrl}/api/v1/games/${id}/guesses`, {
      data,
    });
    await storeResponse(this, res);
  },
);

Then('the response status is {int}', function (this: HangmanWorld, code: number) {
  if (!this.lastApiResponse) throw new Error('No API response recorded');
  expect(this.lastApiResponse.status()).toBe(code);
});

Then('the response error code is {string}', function (this: HangmanWorld, code: string) {
  const found = getPath(this.lastApiBody, 'error.code');
  expect(found).toBe(code);
});

Then(
  'the response body has {string} equal to {string}',
  function (this: HangmanWorld, dotPath: string, expected: string) {
    const found = getPath(this.lastApiBody, dotPath);
    // Type-preserving comparison: try parsing the Gherkin expected value
    // as JSON first (so `"8"` → 8, `"true"` → true, `"null"` → null), fall
    // back to the raw string for bare text (`"IN_PROGRESS"`, `"c"`, etc.).
    // Failing over to `String(found)` coercion would let contract regressions
    // slip — a number field silently becoming a string would still pass.
    let target: unknown;
    try {
      target = JSON.parse(expected);
    } catch {
      target = expected;
    }
    expect(found).toBe(target);
  },
);

Then(
  'the response body array {string} has length {int}',
  function (this: HangmanWorld, dotPath: string, expected: number) {
    const found = getPath(this.lastApiBody, dotPath);
    if (!Array.isArray(found)) {
      throw new Error(
        `Expected array at '${dotPath}', got ${typeof found}: ${JSON.stringify(found)}`,
      );
    }
    expect(found.length).toBe(expected);
  },
);

Then('the response body field {string} is absent', function (this: HangmanWorld, dotPath: string) {
  const found = getPath(this.lastApiBody, dotPath);
  expect(found).toBeUndefined();
});

Then('the response body field {string} is set', function (this: HangmanWorld, dotPath: string) {
  // Asserts the field is present AND not null. Complements "is absent";
  // use it to prove the backend populated a nullable field (e.g.,
  // CreateGameResponse.forfeited_game_id in the forfeit-chain scenario).
  const found = getPath(this.lastApiBody, dotPath);
  expect(found).not.toBeUndefined();
  expect(found).not.toBeNull();
});

Then(
  'the Set-Cookie header contains \\(case-insensitive) {string}',
  function (this: HangmanWorld, needle: string) {
    if (!this.lastApiResponse) throw new Error('No API response recorded');
    const headers = this.lastApiResponse.headers();
    const cookie = (headers['set-cookie'] ?? '').toLowerCase();
    expect(cookie).toContain(needle.toLowerCase());
  },
);

// Session idempotence steps — let a scenario snapshot the cookie value,
// do other API calls, and assert the value is unchanged. Used by
// session.feature. Cookie name is "session_id" (verified against
// backend/src/hangman/sessions.py:12 COOKIE_NAME on 2026-04-23).
When('I remember the session cookie value', async function (this: HangmanWorld) {
  const cookies = await this.context.cookies(this.backendUrl);
  const sess = cookies.find((c) => c.name === 'session_id');
  if (!sess) {
    throw new Error('No session_id cookie set yet — call /api/v1/session first.');
  }
  this.rememberedSessionValue = sess.value;
});

Then('the remembered session cookie value is unchanged', async function (this: HangmanWorld) {
  if (this.rememberedSessionValue === null) {
    throw new Error("Nothing remembered — run 'I remember the session cookie value' first.");
  }
  const cookies = await this.context.cookies(this.backendUrl);
  const sess = cookies.find((c) => c.name === 'session_id');
  expect(sess?.value).toBe(this.rememberedSessionValue);
});
