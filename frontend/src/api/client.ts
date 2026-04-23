import type {
  CategoriesDTO,
  CreateGameDTO,
  ErrorBody,
  GameCreateBody,
  GameDTO,
  HistoryDTO,
  SessionDTO,
} from '../types';

const BASE = '/api/v1';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: Partial<ErrorBody>,
  ) {
    super(body?.error?.message ?? `HTTP ${status}`);
    this.name = 'ApiError';
  }

  get code(): string | undefined {
    return this.body?.error?.code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  getCategories: () => request<CategoriesDTO>('/categories'),
  getSession: () => request<SessionDTO>('/session'),
  getCurrentGame: () =>
    request<GameDTO>('/games/current').catch((e: unknown) => {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }),
  startGame: (body: GameCreateBody) =>
    request<CreateGameDTO>('/games', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  guess: (id: number, letter: string) =>
    request<GameDTO>(`/games/${id}/guesses`, {
      method: 'POST',
      body: JSON.stringify({ letter }),
    }),
  getHistory: (page = 1, pageSize = 20) =>
    request<HistoryDTO>(`/history?page=${page}&page_size=${pageSize}`),
};
