import { HangmanFigure } from './HangmanFigure';
import type { GameDTO } from '../types';

interface GameBoardProps {
  game: GameDTO | null;
}

const MAX_STAGE = 8;

// Mirrors backend game.py::figure_stage(wrong, allowed).
// MAX_STAGE must stay in sync with backend MAX_FIGURE_STAGE.
// If the backend ever exposes a precomputed `figure_stage` field on
// GameDTO, this helper + MAX_STAGE can be deleted.
function computeStage(g: GameDTO): number {
  const start = MAX_STAGE - g.wrong_guesses_allowed;
  return start + g.wrong_guesses;
}

export function GameBoard({ game }: GameBoardProps) {
  if (game === null) {
    return (
      <div data-testid="game-board-empty" role="region" aria-label="Game board">
        Pick a category to start.
      </div>
    );
  }
  const stage = computeStage(game);
  return (
    <div data-testid="game-board" role="region" aria-label="Game board">
      <HangmanFigure stage={stage} />
      <div data-testid="masked-word" style={{ letterSpacing: '0.5em', fontSize: '1.5em' }}>
        {game.masked_word.split('').join(' ')}
      </div>
      <div data-testid="lives-remaining">Lives: {game.lives_remaining}</div>
      {game.state === 'WON' && <div data-testid="game-won">You won! The word was: {game.word}</div>}
      {game.state === 'LOST' && (
        <div data-testid="game-lost">You lost. The word was: {game.word}</div>
      )}
    </div>
  );
}
