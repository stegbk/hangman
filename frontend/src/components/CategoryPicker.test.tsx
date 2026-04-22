import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CategoryPicker } from './CategoryPicker';
import type { DifficultyOption } from '../types';

const DIFFS: DifficultyOption[] = [
  { id: 'easy', label: 'Easy', wrong_guesses_allowed: 8 },
  { id: 'medium', label: 'Medium', wrong_guesses_allowed: 6 },
  { id: 'hard', label: 'Hard', wrong_guesses_allowed: 4 },
];

describe('CategoryPicker', () => {
  it('renders categories and difficulties', () => {
    render(
      <CategoryPicker
        categories={['animals', 'food']}
        difficulties={DIFFS}
        disabled={false}
        onStartGame={() => {}}
      />,
    );
    expect(screen.getByTestId('category-select')).toHaveValue('animals');
    expect(screen.getByTestId('difficulty-easy')).toBeChecked();
  });

  it('start-game-btn disabled while loading', () => {
    render(
      <CategoryPicker
        categories={['animals']}
        difficulties={DIFFS}
        disabled
        onStartGame={() => {}}
      />,
    );
    expect(screen.getByTestId('start-game-btn')).toBeDisabled();
  });

  it('calls onStartGame with selected values', async () => {
    const user = userEvent.setup();
    const spy = vi.fn();
    render(
      <CategoryPicker
        categories={['animals', 'food']}
        difficulties={DIFFS}
        disabled={false}
        onStartGame={spy}
      />,
    );
    await user.selectOptions(screen.getByTestId('category-select'), 'food');
    await user.click(screen.getByTestId('difficulty-hard'));
    await user.click(screen.getByTestId('start-game-btn'));
    expect(spy).toHaveBeenCalledWith('food', 'hard');
  });
});
