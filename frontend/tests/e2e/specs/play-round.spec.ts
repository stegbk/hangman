import { test, expect } from '../fixtures/auth';

test.describe('Hangman scaffold — end-to-end wiring', () => {
  test('UC1 smoke: start game, play, reach terminal state @smoke', async ({ page }) => {
    await page.goto('/');

    // Initial state
    await expect(page.getByTestId('score-panel')).toBeVisible();
    await expect(page.getByTestId('score-total')).toHaveText('0');
    await expect(page.getByTestId('game-board-empty')).toBeVisible();

    // Start game with UI defaults (first category sorted = 'animals', easy = 8 lives)
    await page.getByTestId('start-game-btn').click();

    // Active game UI visible
    await expect(page.getByTestId('game-board')).toBeVisible();
    await expect(page.getByTestId('hangman-figure')).toBeVisible();
    await expect(page.getByTestId('masked-word')).toBeVisible();
    await expect(page.getByTestId('lives-remaining')).toContainText('8');

    // Auto-waiting locator for either terminal banner. `or()` matches when
    // *either* side is visible; expect().toBeVisible() auto-retries.
    const terminalBanner = page.getByTestId('game-won').or(page.getByTestId('game-lost'));

    // Click letters until the terminal banner appears. The 15-letter sequence
    // below terminates any seed animal word within 8 wrong guesses.
    const letters = ['e', 'a', 'o', 'i', 'u', 't', 'n', 'r', 's', 'l', 'c', 'd', 'h', 'p', 'm'];
    for (const letter of letters) {
      // Check terminal FIRST — after a terminal transition all keyboard
      // buttons disable, which would hang a subsequent click waiting for "enabled".
      if ((await terminalBanner.count()) > 0) break;
      const btn = page.getByTestId(`keyboard-letter-${letter}`);
      if (await btn.isDisabled()) continue;
      await btn.click();
      // Wait for the onGuess round-trip + React re-render to settle. The
      // clicked button becomes disabled once the letter is in guessed_letters,
      // which is a natural sync barrier — avoids races where the NEXT
      // iteration checks isDisabled() before the current guess flushed.
      await expect(btn).toBeDisabled();
    }

    // Auto-wait for the terminal transition to land (handles any trailing
    // re-render between the last click and React flushing the state).
    await expect(terminalBanner).toBeVisible();

    // Exactly one banner visible (not both).
    const wonCount = await page.getByTestId('game-won').count();
    const lostCount = await page.getByTestId('game-lost').count();
    expect(wonCount + lostCount).toBe(1);

    // History grew by 1
    await expect(page.locator("[data-testid^='history-item-']")).toHaveCount(1);

    // Persistence: reload survives
    await page.reload();
    await expect(page.locator("[data-testid^='history-item-']")).toHaveCount(1);
  });
});
