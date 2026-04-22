import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from './api/client';
import { CategoryPicker } from './components/CategoryPicker';
import { GameBoard } from './components/GameBoard';
import { HistoryList } from './components/HistoryList';
import { Keyboard } from './components/Keyboard';
import { ScorePanel } from './components/ScorePanel';
import type { CategoriesDTO, Difficulty, DifficultyOption, GameDTO, SessionDTO } from './types';

function humanError(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return 'Unknown error';
}

export default function App() {
  const [categories, setCategories] = useState<string[]>([]);
  const [difficulties, setDifficulties] = useState<DifficultyOption[]>([]);
  const [session, setSession] = useState<SessionDTO | null>(null);
  const [currentGame, setCurrentGame] = useState<GameDTO | null>(null);
  const [history, setHistory] = useState<GameDTO[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refreshSessionAndHistory = useCallback(async () => {
    const [s, h] = await Promise.all([api.getSession(), api.getHistory()]);
    setSession(s);
    setHistory(h.items);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [cats, sess, cur, hist]: [
          CategoriesDTO,
          SessionDTO,
          GameDTO | null,
          { items: GameDTO[] },
        ] = await Promise.all([
          api.getCategories(),
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
      if (currentGame !== null) {
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
      if (currentGame === null) return;
      setError(null);
      try {
        const updated = await api.guess(currentGame.id, letter);
        setCurrentGame(updated);
        if (updated.state !== 'IN_PROGRESS') {
          await refreshSessionAndHistory();
        }
      } catch (e) {
        setError(humanError(e));
      }
    },
    [currentGame, refreshSessionAndHistory],
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
        disabled={loading || currentGame === null || currentGame.state !== 'IN_PROGRESS'}
        onGuess={onGuess}
      />
      <HistoryList games={history} />
    </div>
  );
}
