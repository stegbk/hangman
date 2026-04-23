interface KeyboardProps {
  guessedLetters: string;
  disabled: boolean;
  onGuess: (letter: string) => void;
}

const LETTERS = 'abcdefghijklmnopqrstuvwxyz'.split('');

export function Keyboard({ guessedLetters, disabled, onGuess }: KeyboardProps) {
  return (
    <div data-testid="keyboard" role="group" aria-label="Keyboard">
      {LETTERS.map((letter) => {
        const used = guessedLetters.includes(letter);
        return (
          <button
            key={letter}
            type="button"
            data-testid={`keyboard-letter-${letter}`}
            disabled={disabled || used}
            onClick={() => onGuess(letter)}
          >
            {letter}
          </button>
        );
      })}
    </div>
  );
}
