/**
 * UI-layer step definitions.
 *
 * Every selector uses `data-testid` or role — never raw CSS classes
 * (rules/testing.md "Use stable selectors"). The keyboard-letter step
 * uses a real response-based sync barrier (page.waitForResponse on the
 * /guesses endpoint) rather than just polling disabled state, because
 * the keyboard is disabled SYNCHRONOUSLY on click (guessPending=true),
 * which races with the actual /guesses POST completing and the resulting
 * UI state update. The response wait guarantees the server has committed
 * the guess AND React has reconciled to the post-response state.
 */
import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';
import type { HangmanWorld } from '../support/world';

Given('I open the app', async function (this: HangmanWorld) {
  await this.page.goto(this.frontendUrl);
  await expect(this.page.getByTestId('score-panel')).toBeVisible();
});

When('I click the {string} button', async function (this: HangmanWorld, testid: string) {
  await this.page.getByTestId(testid).click();
});

When('I click the keyboard letter {string}', async function (this: HangmanWorld, letter: string) {
  const btn = this.page.getByTestId(`keyboard-letter-${letter}`);
  // Precondition: button is enabled (guessPending cleared from any
  // previous guess, letter not yet in guessedLetters).
  await expect(btn).toBeEnabled({ timeout: 3000 });
  // Register the response listener BEFORE click so we can't miss a
  // fast response. Matches POST /api/v1/games/{id}/guesses for either
  // success (200) or domain error (422/409) so test-of-error scenarios
  // still unblock here.
  const guessResponse = this.page.waitForResponse(
    (resp) =>
      /\/api\/v1\/games\/\d+\/guesses/.test(resp.url()) && resp.request().method() === 'POST',
    { timeout: 5000 },
  );
  await btn.click();
  await guessResponse;
  // After response + React commit, the clicked letter should now be in
  // guessedLetters and the button permanently disabled. This is the
  // post-response state, not the in-flight state.
  await expect(btn).toBeDisabled({ timeout: 3000 });
});

When('I select category {string}', async function (this: HangmanWorld, category: string) {
  await this.page.getByTestId('category-select').selectOption(category);
});

When('I select difficulty {string}', async function (this: HangmanWorld, difficulty: string) {
  await this.page.getByTestId(`difficulty-${difficulty}`).click();
});

When('I reload the page', async function (this: HangmanWorld) {
  await this.page.reload();
  await expect(this.page.getByTestId('score-panel')).toBeVisible();
});

Then('I see the score panel', async function (this: HangmanWorld) {
  await expect(this.page.getByTestId('score-panel')).toBeVisible();
});

Then('the total score is {string}', async function (this: HangmanWorld, expected: string) {
  await expect(this.page.getByTestId('score-total')).toHaveText(expected);
});

Then('the current streak is {string}', async function (this: HangmanWorld, expected: string) {
  await expect(this.page.getByTestId('streak-current')).toHaveText(expected);
});

Then('I see the game-{word} banner', async function (this: HangmanWorld, outcome: string) {
  await expect(this.page.getByTestId(`game-${outcome}`)).toBeVisible();
});

Then('history contains {int} item(s)', async function (this: HangmanWorld, expected: number) {
  const items = this.page.locator('[data-testid^="history-item-"]');
  await expect(items).toHaveCount(expected);
});

Then('the masked word shows {string}', async function (this: HangmanWorld, expected: string) {
  await expect(this.page.getByTestId('masked-word')).toHaveText(expected);
});

Then(
  'the keyboard letter {string} is disabled',
  async function (this: HangmanWorld, letter: string) {
    await expect(this.page.getByTestId(`keyboard-letter-${letter}`)).toBeDisabled();
  },
);

Then(
  'the keyboard letter {string} is enabled',
  async function (this: HangmanWorld, letter: string) {
    await expect(this.page.getByTestId(`keyboard-letter-${letter}`)).toBeEnabled();
  },
);
