import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from './api/client';
import { CategoryPicker } from './components/CategoryPicker';
import { GameBoard } from './components/GameBoard';
import { HistoryList } from './components/HistoryList';
import { Keyboard } from './components/Keyboard';
import { ScorePanel } from './components/ScorePanel';
import type { Difficulty, DifficultyOption, GameDTO, SessionDTO } from './types';

function humanError(e: unknown): string {
  if (e instanceof ApiError) {
    switch (e.code) {
      case 'NO_ACTIVE_GAME':
        return 'No game in progress — start a new one.';
      case 'GAME_ALREADY_FINISHED':
        return 'This game has already ended.';
      case 'ALREADY_GUESSED':
        return "You've already guessed that letter.";
      case 'INVALID_LETTER':
        return 'Please guess a single letter a–z.';
      case 'UNKNOWN_CATEGORY':
        return 'That category is not available — pick another.';
      case 'GAME_NOT_FOUND':
        return 'That game no longer exists.';
      case 'CONCURRENT_START':
        return 'Another game was started simultaneously — please retry.';
      case 'VALIDATION_ERROR':
        return 'That input looks invalid — please check and retry.';
      case 'INTERNAL_ERROR': {
        const rid = e.body?.error?.request_id;
        return `Something went wrong on our end${rid ? ` (ref ${rid})` : ''}. Please try again.`;
      }
      default:
        return e.message || `Request failed (HTTP ${e.status}).`;
    }
  }
  if (e instanceof TypeError && /fetch/i.test(e.message)) {
    return 'Network error — check your connection and try again.';
  }
  if (e instanceof Error) return e.message;
  return 'Unknown error. Please refresh and try again.';
}

export default function App() {
  const [categories, setCategories] = useState<string[]>([]);
  const [difficulties, setDifficulties] = useState<DifficultyOption[]>([]);
  const [session, setSession] = useState<SessionDTO | null>(null);
  const [currentGame, setCurrentGame] = useState<GameDTO | null>(null);
  const [history, setHistory] = useState<GameDTO[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [guessPending, setGuessPending] = useState<boolean>(false);

  const refreshSessionAndHistory = useCallback(async () => {
    const [s, h] = await Promise.all([api.getSession(), api.getHistory()]);
    setSession(s);
    setHistory(h.items);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // Sequential: categories first so the session cookie is set before
        // concurrent requests fire — avoids creating multiple orphan sessions.
        const cats = await api.getCategories();
        if (cancelled) return;
        const [sess, cur, hist] = await Promise.all([
          api.getSession(),
          api.getCurrentGame(),
          api.getHistory(),
        ]);
        if (cancelled) return;
        setCategories(cats.categories);
        setDifficulties(cats.difficulties);
        setSession(sess);
        setCurrentGame(cur);
        setHistory(hist.items);
      } catch (e) {
        if (!cancelled) setError(humanError(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const onStartGame = useCallback(
    async (category: string, difficulty: Difficulty) => {
      // Only confirm forfeit when the current game is genuinely active.
      // A terminal (WON/LOST) game is still in state so we can render the
      // banner, but starting a new one doesn't forfeit anything — PRD US-005
      // scopes the confirm to IN_PROGRESS games only.
      if (currentGame !== null && currentGame.state === 'IN_PROGRESS') {
        const ok = window.confirm(
          'You have an active game. Starting a new one will forfeit it. Continue?',
        );
        if (!ok) return;
      }
      setLoading(true);
      setError(null);
      try {
        const created = await api.startGame({ category, difficulty });
        setCurrentGame(created);
        await refreshSessionAndHistory();
      } catch (e) {
        setError(humanError(e));
      } finally {
        setLoading(false);
      }
    },
    [currentGame, refreshSessionAndHistory],
  );

  const onGuess = useCallback(
    async (letter: string) => {
      if (currentGame === null || guessPending) return;
      setError(null);
      setGuessPending(true);
      try {
        const updated = await api.guess(currentGame.id, letter);
        setCurrentGame(updated);
        if (updated.state !== 'IN_PROGRESS') {
          await refreshSessionAndHistory();
        }
      } catch (e) {
        setError(humanError(e));
      } finally {
        setGuessPending(false);
      }
    },
    [currentGame, guessPending, refreshSessionAndHistory],
  );

  const dismissError = useCallback(() => setError(null), []);

  return (
    <div className="app" data-testid="app">
      {error && (
        <div role="alert" data-testid="error-banner">
          <span>{error}</span>
          <button type="button" onClick={dismissError}>
            dismiss
          </button>
        </div>
      )}
      <ScorePanel session={session} />
      <CategoryPicker
        categories={categories}
        difficulties={difficulties}
        disabled={loading}
        onStartGame={onStartGame}
      />
      <GameBoard game={currentGame} />
      <Keyboard
        guessedLetters={currentGame?.guessed_letters ?? ''}
        disabled={
          loading || guessPending || currentGame === null || currentGame.state !== 'IN_PROGRESS'
        }
        onGuess={onGuess}
      />
      <HistoryList games={history} />
    </div>
  );
}
