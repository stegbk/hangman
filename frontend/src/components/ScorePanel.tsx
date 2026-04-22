import type { SessionDTO } from '../types';

interface ScorePanelProps {
  session: SessionDTO | null;
}

export function ScorePanel({ session }: ScorePanelProps) {
  const score = session?.total_score ?? 0;
  const current = session?.current_streak ?? 0;
  const best = session?.best_streak ?? 0;
  return (
    <div data-testid="score-panel" role="region" aria-label="Score panel">
      <div>
        <label>Total Score</label>
        <span data-testid="score-total">{score}</span>
      </div>
      <div>
        <label>Current Streak</label>
        <span data-testid="streak-current">{current}</span>
      </div>
      <div>
        <label>Best Streak</label>
        <span data-testid="streak-best">{best}</span>
      </div>
    </div>
  );
}
