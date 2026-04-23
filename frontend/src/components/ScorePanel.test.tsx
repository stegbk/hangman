import { render, screen } from '@testing-library/react';
import { ScorePanel } from './ScorePanel';

describe('ScorePanel', () => {
  it('renders zeros on null session', () => {
    render(<ScorePanel session={null} />);
    expect(screen.getByTestId('score-total').textContent).toBe('0');
    expect(screen.getByTestId('streak-current').textContent).toBe('0');
    expect(screen.getByTestId('streak-best').textContent).toBe('0');
  });

  it('renders populated session values', () => {
    render(<ScorePanel session={{ current_streak: 3, best_streak: 7, total_score: 250 }} />);
    expect(screen.getByTestId('score-total').textContent).toBe('250');
    expect(screen.getByTestId('streak-current').textContent).toBe('3');
    expect(screen.getByTestId('streak-best').textContent).toBe('7');
  });
});
