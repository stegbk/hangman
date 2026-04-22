import { ApiError, api } from './client';

describe('api client', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('getCurrentGame returns null on 404', async () => {
    global.fetch = vi.fn(
      async () =>
        new Response(JSON.stringify({ error: { code: 'NO_ACTIVE_GAME' } }), {
          status: 404,
        }),
    ) as typeof fetch;
    const res = await api.getCurrentGame();
    expect(res).toBeNull();
  });

  it('getCurrentGame throws ApiError on 500', async () => {
    global.fetch = vi.fn(
      async () =>
        new Response(JSON.stringify({ error: { code: 'INTERNAL_ERROR' } }), {
          status: 500,
        }),
    ) as typeof fetch;
    await expect(api.getCurrentGame()).rejects.toBeInstanceOf(ApiError);
  });

  it('startGame posts JSON body with credentials include', async () => {
    const spy = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            id: 1,
            category: 'animals',
            difficulty: 'easy',
            wrong_guesses_allowed: 8,
            wrong_guesses: 0,
            guessed_letters: '',
            state: 'IN_PROGRESS',
            score: 0,
            started_at: '2026-04-22T00:00:00Z',
            finished_at: null,
            masked_word: '___',
            lives_remaining: 8,
            // `word` is ABSENT (not null) mid-game — PRD US-001 + schemas.py serializer.
            forfeited_game_id: null,
          }),
          { status: 201 },
        ),
    );
    global.fetch = spy as typeof fetch;
    await api.startGame({ category: 'animals', difficulty: 'easy' });
    const [url, init] = spy.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/v1/games');
    expect(init?.method).toBe('POST');
    expect(init?.credentials).toBe('include');
  });

  it('ApiError exposes code via body', () => {
    const err = new ApiError(422, {
      error: {
        code: 'ALREADY_GUESSED',
        message: 'x',
        details: [],
        request_id: null,
      },
    });
    expect(err.code).toBe('ALREADY_GUESSED');
    expect(err.status).toBe(422);
  });
});
