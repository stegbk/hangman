import { useEffect, useState } from 'react';
import type { Difficulty, DifficultyOption } from '../types';

interface CategoryPickerProps {
  categories: string[];
  difficulties: DifficultyOption[];
  disabled: boolean;
  onStartGame: (category: string, difficulty: Difficulty) => void;
}

export function CategoryPicker({
  categories,
  difficulties,
  disabled,
  onStartGame,
}: CategoryPickerProps) {
  const [category, setCategory] = useState<string>(categories[0] ?? '');
  const [difficulty, setDifficulty] = useState<Difficulty>(
    (difficulties[0]?.id ?? 'easy') as Difficulty,
  );

  // Keep selections valid if props change. Wrapped in useEffect to avoid
  // calling setState synchronously in the render body (React StrictMode warns).
  useEffect(() => {
    if (categories.length > 0 && !categories.includes(category)) {
      setCategory(categories[0]);
    }
  }, [categories, category]);

  return (
    <div data-testid="category-picker" role="region" aria-label="Category picker">
      <label>
        Category
        <select
          data-testid="category-select"
          value={category}
          disabled={disabled || categories.length === 0}
          onChange={(e) => setCategory(e.target.value)}
        >
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>
      <fieldset>
        <legend>Difficulty</legend>
        {difficulties.map((d) => (
          <label key={d.id}>
            <input
              type="radio"
              data-testid={`difficulty-${d.id}`}
              name="difficulty"
              value={d.id}
              checked={difficulty === d.id}
              disabled={disabled}
              onChange={() => setDifficulty(d.id)}
            />
            {d.label} ({d.wrong_guesses_allowed} lives)
          </label>
        ))}
      </fieldset>
      <button
        type="button"
        data-testid="start-game-btn"
        disabled={disabled || !category}
        onClick={() => onStartGame(category, difficulty)}
      >
        Start New Game
      </button>
    </div>
  );
}
