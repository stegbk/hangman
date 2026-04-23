const STAGES: readonly string[] = [
  // Stage 0 — empty gallows
  `  +---+
  |   |
      |
      |
      |
      |
========`,
  // Stage 1 — head
  `  +---+
  |   |
  O   |
      |
      |
      |
========`,
  // Stage 2 — torso
  `  +---+
  |   |
  O   |
  |   |
      |
      |
========`,
  // Stage 3 — one arm
  `  +---+
  |   |
  O   |
 /|   |
      |
      |
========`,
  // Stage 4 — both arms
  `  +---+
  |   |
  O   |
 /|\\  |
      |
      |
========`,
  // Stage 5 — one leg
  `  +---+
  |   |
  O   |
 /|\\  |
 /    |
      |
========`,
  // Stage 6 — both legs
  `  +---+
  |   |
  O   |
 /|\\  |
 / \\  |
      |
========`,
  // Stage 7 — face expression
  `  +---+
  |   |
  X   |
 /|\\  |
 / \\  |
      |
========`,
  // Stage 8 — fully hanged + 'rope' strain
  `  +---+
  |   |
  X   |
 /|\\  |
 / \\  |
   .  |
========`,
];

interface HangmanFigureProps {
  stage: number;
}

export function HangmanFigure({ stage }: HangmanFigureProps) {
  const clamped = Math.max(0, Math.min(stage, STAGES.length - 1));
  return (
    <pre data-testid="hangman-figure" aria-label={`Hangman figure, stage ${clamped} of 8`}>
      {STAGES[clamped]}
    </pre>
  );
}
