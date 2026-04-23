/**
 * Cross-cutting steps and hooks.
 *
 * Three dialog hooks are registered on mutually-exclusive tags:
 *
 *   @dialog-accept  → listener hits OK on every window.confirm / alert.
 *                     Use in UC3 forfeit (user confirms they want to
 *                     abandon the active game).
 *
 *   @dialog-reject  → listener hits Cancel. Use for the "user cancelled"
 *                     branch of any confirm flow.
 *
 *   @dialog-tracked → listener only counts dialogs without handling them.
 *                     Use when the scenario asserts that NO dialog fired
 *                     (e.g., UC3b where starting a new game after a loss
 *                     must skip the forfeit confirm entirely). An
 *                     unexpected dialog will also block subsequent
 *                     Playwright actions — the desired loud-failure.
 *
 * Scenarios must pick exactly one of the three tags if they interact
 * with any confirm()/alert(). `this.dialogCount` is reset in the
 * per-scenario Before hook in support/hooks.ts.
 */
import { Given, Then, Before } from '@cucumber/cucumber';
import { expect } from '@playwright/test';
import type { HangmanWorld } from '../support/world';

// A no-op, documentation-only step. The Before hook in support/hooks.ts
// has already asserted backend reachability; this just reads nicely in
// Gherkin scenarios ("Given the backend and frontend are running").
Given('the backend and frontend are running', function (this: HangmanWorld) {
  // intentionally empty
});

// Mutex guard: cucumber runs every matching Before hook, so a scenario
// accidentally tagged with two @dialog-* tags would register two listeners
// and behave unpredictably. Fail the scenario loudly instead.
Before(
  {
    tags: '(@dialog-accept and @dialog-reject) or (@dialog-accept and @dialog-tracked) or (@dialog-reject and @dialog-tracked)',
  },
  function () {
    throw new Error(
      'Scenario has multiple @dialog-* tags. Pick exactly one of @dialog-accept, @dialog-reject, @dialog-tracked.',
    );
  },
);

Before({ tags: '@dialog-accept' }, async function (this: HangmanWorld) {
  this.page.on('dialog', async (dialog) => {
    this.dialogCount += 1;
    await dialog.accept();
  });
});

Before({ tags: '@dialog-reject' }, async function (this: HangmanWorld) {
  this.page.on('dialog', async (dialog) => {
    this.dialogCount += 1;
    await dialog.dismiss();
  });
});

Before({ tags: '@dialog-tracked' }, async function (this: HangmanWorld) {
  // Shorter callback arity — we deliberately don't handle the dialog; just
  // count it. Playwright invokes the handler with the dialog argument, but
  // the callback is free to accept fewer parameters.
  this.page.on('dialog', async () => {
    this.dialogCount += 1;
  });
});

Then('no dialog has fired', function (this: HangmanWorld) {
  expect(this.dialogCount).toBe(0);
});

Then('a dialog has fired', function (this: HangmanWorld) {
  expect(this.dialogCount).toBeGreaterThanOrEqual(1);
});
