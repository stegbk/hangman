import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, afterEach, beforeEach, describe, it, expect } from 'vitest';
import App from './App';
import type { GameDTO } from './types';

// Mock the api module; each test configures responses via the mock instances.
vi.mock('./api/client', async () => {
  const actual = await vi.importActual<typeof import('./api/client')>('./api/client');
  return {
    ...actual,
    api: {
      getCategories: vi.fn(),
      getSession: vi.fn(),
      getCurrentGame: vi.fn(),
      getHistory: vi.fn(),
      startGame: vi.fn(),
      guess: vi.fn(),
    },
  };
});

import { api } from './api/client';

const mockedApi = api as unknown as {
  getCategories: ReturnType<typeof vi.fn>;
  getSession: ReturnType<typeof vi.fn>;
  getCurrentGame: ReturnType<typeof vi.fn>;
  getHistory: ReturnType<typeof vi.fn>;
  startGame: ReturnType<typeof vi.fn>;
  guess: ReturnType<typeof vi.fn>;
};

function gameFixture(overrides: Partial<GameDTO> = {}): GameDTO {
  return {
    id: 1,
    category: 'animals',
    difficulty: 'easy',
    wrong_guesses_allowed: 8,
    wrong_guesses: 0,
    guessed_letters: '',
    state: 'IN_PROGRESS',
    score: 0,
    started_at: '2026-04-22T00:00:00Z',
    finished_at: null,
    masked_word: '___',
    lives_remaining: 8,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockedApi.getCategories.mockResolvedValue({
    categories: ['animals', 'food', 'tech'],
    difficulties: [
      { id: 'easy', label: 'Easy', wrong_guesses_allowed: 8 },
      { id: 'medium', label: 'Medium', wrong_guesses_allowed: 6 },
      { id: 'hard', label: 'Hard', wrong_guesses_allowed: 4 },
    ],
  });
  mockedApi.getSession.mockResolvedValue({ current_streak: 0, best_streak: 0, total_score: 0 });
  mockedApi.getHistory.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('App — forfeit-confirm scoping (PRD US-005)', () => {
  it('shows forfeit confirm when current game is IN_PROGRESS', async () => {
    mockedApi.getCurrentGame.mockResolvedValue(gameFixture({ state: 'IN_PROGRESS' }));
    mockedApi.startGame.mockResolvedValue({
      ...gameFixture({ id: 2 }),
      forfeited_game_id: 1,
    });
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    const user = userEvent.setup();
    render(<App />);

    await screen.findByTestId('game-board');
    await user.click(screen.getByTestId('start-game-btn'));

    expect(confirmSpy).toHaveBeenCalledOnce();
    expect(confirmSpy).toHaveBeenCalledWith(expect.stringMatching(/forfeit/i));
  });

  it('does NOT show forfeit confirm when current game is WON', async () => {
    mockedApi.getCurrentGame.mockResolvedValue(
      gameFixture({ state: 'WON', word: 'cat', masked_word: 'cat' }),
    );
    mockedApi.startGame.mockResolvedValue({
      ...gameFixture({ id: 2 }),
      forfeited_game_id: null,
    });
    const confirmSpy = vi.spyOn(window, 'confirm');

    const user = userEvent.setup();
    render(<App />);

    await screen.findByTestId('game-won');
    await user.click(screen.getByTestId('start-game-btn'));

    expect(confirmSpy).not.toHaveBeenCalled();
  });

  it('does NOT show forfeit confirm when current game is LOST', async () => {
    mockedApi.getCurrentGame.mockResolvedValue(gameFixture({ state: 'LOST', word: 'cat' }));
    mockedApi.startGame.mockResolvedValue({
      ...gameFixture({ id: 2 }),
      forfeited_game_id: null,
    });
    const confirmSpy = vi.spyOn(window, 'confirm');

    const user = userEvent.setup();
    render(<App />);

    await screen.findByTestId('game-lost');
    await user.click(screen.getByTestId('start-game-btn'));

    expect(confirmSpy).not.toHaveBeenCalled();
  });

  it('does NOT show forfeit confirm when there is no current game', async () => {
    mockedApi.getCurrentGame.mockResolvedValue(null);
    mockedApi.startGame.mockResolvedValue({
      ...gameFixture({ id: 1 }),
      forfeited_game_id: null,
    });
    const confirmSpy = vi.spyOn(window, 'confirm');

    const user = userEvent.setup();
    render(<App />);

    await screen.findByTestId('game-board-empty');
    await user.click(screen.getByTestId('start-game-btn'));

    expect(confirmSpy).not.toHaveBeenCalled();
  });
});

describe('App — mount effect', () => {
  it('surfaces an error banner when a boot call rejects with ApiError', async () => {
    const { ApiError } = await vi.importActual<typeof import('./api/client')>('./api/client');
    mockedApi.getCategories.mockRejectedValue(
      new ApiError(500, {
        error: { code: 'INTERNAL_ERROR', message: 'boom', details: [], request_id: 'req_xyz' },
      }),
    );
    mockedApi.getCurrentGame.mockResolvedValue(null);

    render(<App />);
    const banner = await screen.findByTestId('error-banner');
    // humanError maps INTERNAL_ERROR to a friendly message containing the request_id.
    expect(banner.textContent).toMatch(/req_xyz/);
  });
});
