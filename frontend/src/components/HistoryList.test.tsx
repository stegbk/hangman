import { render, screen } from '@testing-library/react';
import { HistoryList } from './HistoryList';
import type { GameDTO } from '../types';

function g(overrides: Partial<GameDTO> = {}): GameDTO {
  return {
    id: 1,
    category: 'animals',
    difficulty: 'easy',
    wrong_guesses_allowed: 8,
    wrong_guesses: 2,
    guessed_letters: 'act',
    state: 'WON',
    score: 65,
    started_at: '2026-04-22T00:00:00Z',
    finished_at: '2026-04-22T00:02:00Z',
    masked_word: 'cat',
    lives_remaining: 6,
    word: 'cat',
    ...overrides,
  };
}

describe('HistoryList', () => {
  it('shows empty state when no games', () => {
    render(<HistoryList games={[]} />);
    expect(screen.getByTestId('history-empty')).toHaveTextContent(/no games/i);
  });

  it('renders each game with an id-keyed testid', () => {
    render(<HistoryList games={[g({ id: 42 }), g({ id: 7 })]} />);
    expect(screen.getByTestId('history-item-42')).toBeInTheDocument();
    expect(screen.getByTestId('history-item-7')).toBeInTheDocument();
  });
});
