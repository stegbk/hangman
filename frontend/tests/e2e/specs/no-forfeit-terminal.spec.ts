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
    await page.getByTestId('start-game-btn').click();
    await expect(page.getByTestId('game-board')).toBeVisible();

    // Guess rare letters — may land on WON or LOST depending on the word.
    const wrongLetters = ['q', 'x', 'z', 'j', 'v', 'w', 'k', 'y'];
    const terminalBanner = page.getByTestId('game-won').or(page.getByTestId('game-lost'));
    for (const letter of wrongLetters) {
      const btn = page.getByTestId(`keyboard-letter-${letter}`);
      if (await btn.isDisabled()) continue;
      await btn.click();
      if ((await terminalBanner.count()) > 0) break;
    }

    // Auto-wait for terminal banner to render.
    await expect(terminalBanner).toBeVisible();

    const wonVisible = await page.getByTestId('game-won').count();
    const lostVisible = await page.getByTestId('game-lost').count();
    expect(wonVisible + lostVisible).toBe(1);

    // No dialog has fired yet.
    expect(dialogCount).toBe(0);

    // Click "Start New Game" with a terminal game in state. This MUST NOT fire
    // window.confirm (PRD US-005 scopes the prompt to IN_PROGRESS games only).
    await page.getByTestId('start-game-btn').click();

    // Auto-wait for the NEW (mid-play) game to appear — lives-remaining back to 8
    // and no terminal banner. Serves as synchronization point.
    await expect(page.getByTestId('lives-remaining')).toContainText('8');
    await expect(page.getByTestId('game-won')).toHaveCount(0);
    await expect(page.getByTestId('game-lost')).toHaveCount(0);

    // Still no dialog.
    expect(dialogCount).toBe(0);
  });
});
