import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Keyboard } from './Keyboard';

describe('Keyboard', () => {
  it('renders 26 buttons a-z', () => {
    render(<Keyboard guessedLetters="" disabled={false} onGuess={() => {}} />);
    for (const ch of 'abcdefghijklmnopqrstuvwxyz') {
      expect(screen.getByTestId(`keyboard-letter-${ch}`)).toBeInTheDocument();
    }
  });

  it('disables guessed letters', () => {
    render(<Keyboard guessedLetters="ael" disabled={false} onGuess={() => {}} />);
    expect(screen.getByTestId('keyboard-letter-a')).toBeDisabled();
    expect(screen.getByTestId('keyboard-letter-e')).toBeDisabled();
    expect(screen.getByTestId('keyboard-letter-l')).toBeDisabled();
    expect(screen.getByTestId('keyboard-letter-z')).not.toBeDisabled();
  });

  it('disables all when `disabled` prop is true', () => {
    render(<Keyboard guessedLetters="" disabled onGuess={() => {}} />);
    expect(screen.getByTestId('keyboard-letter-a')).toBeDisabled();
  });

  it('calls onGuess with the clicked letter', async () => {
    const user = userEvent.setup();
    const spy = vi.fn();
    render(<Keyboard guessedLetters="" disabled={false} onGuess={spy} />);
    await user.click(screen.getByTestId('keyboard-letter-h'));
    expect(spy).toHaveBeenCalledWith('h');
  });
});
