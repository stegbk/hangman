import { render, screen } from '@testing-library/react';
import { GameBoard } from './GameBoard';
import type { GameDTO } from '../types';

function g(overrides: Partial<GameDTO> = {}): GameDTO {
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
    // `word` is OPTIONAL in the DTO; absent during IN_PROGRESS.
    // Override to `{ state: "WON", word: "cat", masked_word: "cat" }` for terminal tests.
    ...overrides,
  };
}

describe('GameBoard', () => {
  it('shows empty state when game is null', () => {
    render(<GameBoard game={null} />);
    expect(screen.getByTestId('game-board-empty')).toHaveTextContent(/pick a category/i);
  });

  it('shows masked word + hangman figure + lives during IN_PROGRESS', () => {
    render(<GameBoard game={g()} />);
    expect(screen.getByTestId('hangman-figure')).toBeInTheDocument();
    expect(screen.getByTestId('masked-word').textContent).toBe('_ _ _');
    expect(screen.getByTestId('lives-remaining').textContent).toContain('8');
  });

  it('shows win banner on WON', () => {
    render(<GameBoard game={g({ state: 'WON', word: 'cat', masked_word: 'cat' })} />);
    expect(screen.getByTestId('game-won')).toHaveTextContent(/cat/i);
  });

  it('shows loss banner on LOST', () => {
    render(<GameBoard game={g({ state: 'LOST', word: 'cat' })} />);
    expect(screen.getByTestId('game-lost')).toHaveTextContent(/cat/i);
  });
});
