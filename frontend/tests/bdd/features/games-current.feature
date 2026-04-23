Feature: GET /api/v1/games/current

  Returns the session's current IN_PROGRESS game, or 404 if none exists.
  Strictly session-scoped — a different session never sees this one's
  active game.

  Background:
    Given the backend and frontend are running

  @happy @smoke
  Scenario: Returns the active game for the session
    Given I start a new game with category "animals" and difficulty "hard"
    When I request "/api/v1/games/current"
    Then the response status is 200
    And the response body has "state" equal to "IN_PROGRESS"
    And the response body has "difficulty" equal to "hard"
    And the response body field "word" is absent

  @failure
  Scenario: No active game returns 404
    When I request "/api/v1/games/current"
    Then the response status is 404
    And the response error code is "NO_ACTIVE_GAME"

  @edge
  Scenario: A different session cannot see this session's game
    Given I start a new game with category "animals" and difficulty "easy"
    When I request "/api/v1/games/current" from a fresh session
    Then the response status is 404
    And the response error code is "NO_ACTIVE_GAME"
