Feature: GET /api/v1/session

  The session endpoint issues or echoes a browser-scoped session cookie
  used to key all game/history state. Idempotent — a second call from the
  same session reuses the cookie value.

  Background:
    Given the backend and frontend are running

  @happy @smoke
  Scenario: First call issues a session cookie
    When I request "/api/v1/session"
    Then the response status is 200
    And the Set-Cookie header contains (case-insensitive) "HttpOnly"
    And the Set-Cookie header contains (case-insensitive) "samesite=lax"

  @happy
  Scenario: Subsequent same-session calls reuse the cookie value
    When I request "/api/v1/session"
    And I remember the session cookie value
    When I request "/api/v1/session"
    Then the response status is 200
    And the remembered session cookie value is unchanged

  @edge
  Scenario: Session cookie sets a 30-day Max-Age
    When I request "/api/v1/session"
    Then the response status is 200
    And the Set-Cookie header contains (case-insensitive) "max-age=2592000"
