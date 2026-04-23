import type { SessionDTO } from '../types';

interface ScorePanelProps {
  session: SessionDTO | null;
}

export function ScorePanel({ session }: ScorePanelProps) {
  const score = session?.total_score ?? 0;
  const current = session?.current_streak ?? 0;
  const best = session?.best_streak ?? 0;
  return (
    <dl data-testid="score-panel" role="region" aria-label="Score panel">
      <div>
        <dt>Total Score</dt>
        <dd data-testid="score-total">{score}</dd>
      </div>
      <div>
        <dt>Current Streak</dt>
        <dd data-testid="streak-current">{current}</dd>
      </div>
      <div>
        <dt>Best Streak</dt>
        <dd data-testid="streak-best">{best}</dd>
      </div>
    </dl>
  );
}
