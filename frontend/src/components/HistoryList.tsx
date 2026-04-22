import type { GameDTO } from '../types';

interface HistoryListProps {
  games: GameDTO[];
}

export function HistoryList({ games }: HistoryListProps) {
  if (games.length === 0) {
    return (
      <div data-testid="history-empty" role="region" aria-label="Game history">
        No games played yet.
      </div>
    );
  }
  return (
    <ol data-testid="history-list" aria-label="Game history">
      {games.map((g) => (
        <li key={g.id} data-testid={`history-item-${g.id}`}>
          <span>{g.category}</span>
          <span>{g.difficulty}</span>
          <span>{g.word ?? '—'}</span>
          <span>{g.state}</span>
          <span>{g.score}</span>
          <time>{g.finished_at ?? ''}</time>
        </li>
      ))}
    </ol>
  );
}
