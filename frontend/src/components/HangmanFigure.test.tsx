import { render, screen } from '@testing-library/react';
import { HangmanFigure } from './HangmanFigure';

describe('HangmanFigure', () => {
  it('renders stage 0 as empty gallows', () => {
    render(<HangmanFigure stage={0} />);
    const pre = screen.getByTestId('hangman-figure');
    expect(pre.textContent).toContain('+---+');
    expect(pre.textContent).not.toContain('O');
  });

  it('renders stage 1 with head', () => {
    render(<HangmanFigure stage={1} />);
    expect(screen.getByTestId('hangman-figure').textContent).toContain('O');
  });

  it('clamps stage > 8 to 8', () => {
    const { rerender } = render(<HangmanFigure stage={100} />);
    const text8 = screen.getByTestId('hangman-figure').textContent;
    rerender(<HangmanFigure stage={8} />);
    expect(screen.getByTestId('hangman-figure').textContent).toBe(text8);
  });

  it('clamps negative stage to 0', () => {
    render(<HangmanFigure stage={-5} />);
    expect(screen.getByTestId('hangman-figure').textContent).not.toContain('O');
  });
});
