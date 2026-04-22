export type Difficulty = 'easy' | 'medium' | 'hard';
export type GameState = 'IN_PROGRESS' | 'WON' | 'LOST';

export interface DifficultyOption {
  id: Difficulty;
  label: string;
  wrong_guesses_allowed: number;
}

export interface CategoriesDTO {
  categories: string[];
  difficulties: DifficultyOption[];
}

export interface SessionDTO {
  current_streak: number;
  best_streak: number;
  total_score: number;
}

export interface GameDTO {
  id: number;
  category: string;
  difficulty: Difficulty;
  wrong_guesses_allowed: number;
  wrong_guesses: number;
  guessed_letters: string;
  state: GameState;
  score: number;
  started_at: string;
  finished_at: string | null;
  masked_word: string;
  lives_remaining: number;
  // Absent (undefined) while IN_PROGRESS; present when state is WON or LOST.
  // Backend omits the key entirely mid-game — we model it as optional here, not
  // `string | null`, so `'word' in game` correctly reflects server intent.
  word?: string;
}

export interface CreateGameDTO extends GameDTO {
  forfeited_game_id: number | null;
}

export interface HistoryDTO {
  items: GameDTO[];
  total: number;
  page: number;
  page_size: number;
}

export interface GameCreateBody {
  category: string;
  difficulty: Difficulty;
}

export interface ErrorBody {
  error: {
    code: string;
    message: string;
    details: unknown[];
    request_id: string | null;
  };
}
