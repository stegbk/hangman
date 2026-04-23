import { test, expect } from '../fixtures/auth';

test.describe('Hangman scaffold — forfeit-confirm scoping (UC3b)', () => {
  test('terminal game followed by new-game does NOT trigger forfeit confirm @smoke', async ({
    page,
  }) => {
    // Track any dialog fires — we assert zero by end.
    let dialogCount = 0;
    page.on('dialog', (dialog) => {
      dialogCount += 1;
      dialog.accept().catch(() => {});
    });

    await page.goto('/');

    // Select hard difficulty (4 lives) so 4 guaranteed misses produce LOST
    // deterministically — avoids the ~20% flake where easy (8 lives) words
    // like "squirrel" happen to contain one of the guessed rare letters.
    await page.getByTestId('difficulty-hard').click();
    await page.getByTestId('start-game-btn').click();
    await expect(page.getByTestId('game-board')).toBeVisible();
    await expect(page.getByTestId('lives-remaining')).toContainText('4');

    // j, v, x, z — none of these letters appear in any animal seed word
    // (cat, dog, elephant, giraffe, octopus, penguin, dolphin, kangaroo,
    //  rabbit, squirrel, butterfly, hippopotamus, crocodile, chameleon, flamingo).
    // NOTE: 'q' was removed from this set after iter-2 review caught that
    // 'squirrel' contains 'q' — if the random word was squirrel, the 'q' click
    // would have been a correct guess, leaving hard mode with only 3 wrong
    // guesses and no terminal transition.
    // 4 misses exhausts hard-mode lives → guaranteed LOST state.
    const wrongLetters = ['j', 'v', 'x', 'z'];
    const terminalBanner = page.getByTestId('game-won').or(page.getByTestId('game-lost'));
    for (const letter of wrongLetters) {
      if ((await terminalBanner.count()) > 0) break;
      const btn = page.getByTestId(`keyboard-letter-${letter}`);
      // App.tsx's guessPending state disables the whole keyboard during
      // each in-flight guess. Wait for the button to become enabled rather
      // than skipping on disabled — the latter races with guessPending.
      try {
        await expect(btn).toBeEnabled({ timeout: 3000 });
      } catch {
        continue;
      }
      await btn.click();
      await expect(btn).toBeDisabled();
    }

    // Auto-wait for terminal banner to render.
    await expect(terminalBanner).toBeVisible();

    // Hard + 4 guaranteed misses → always LOST (never coincidentally WON).
    await expect(page.getByTestId('game-lost')).toBeVisible();

    // No dialog has fired yet.
    expect(dialogCount).toBe(0);

    // Click "Start New Game" with a terminal game in state. This MUST NOT fire
    // window.confirm (PRD US-005 scopes the prompt to IN_PROGRESS games only).
    await page.getByTestId('start-game-btn').click();

    // Auto-wait for the NEW (mid-play) game to appear. Hard is still selected
    // so the new game also has 4 lives. No terminal banner should be visible.
    await expect(page.getByTestId('lives-remaining')).toContainText('4');
    await expect(page.getByTestId('game-won')).toHaveCount(0);
    await expect(page.getByTestId('game-lost')).toHaveCount(0);

    // Still no dialog.
    expect(dialogCount).toBe(0);
  });
});
