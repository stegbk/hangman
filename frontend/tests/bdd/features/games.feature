Feature: POST /api/v1/games (start and forfeit-chain)

  The games endpoint starts a new hangman game for the current session.
  Starting a game while another is IN_PROGRESS auto-forfeits the previous
  one. The response never leaks the target word.

  Background:
    Given the backend and frontend are running

  @happy @smoke
  Scenario: Valid start creates an IN_PROGRESS game
    When I POST to "/api/v1/games" with body:
      """
      { "category": "animals", "difficulty": "easy" }
      """
    Then the response status is 201
    And the response body has "state" equal to "IN_PROGRESS"
    And the response body has "category" equal to "animals"
    And the response body has "difficulty" equal to "easy"
    And the response body has "wrong_guesses_allowed" equal to "8"
    And the response body field "word" is absent

  @happy
  Scenario: Start on a medium difficulty reports 6 lives
    When I POST to "/api/v1/games" with body:
      """
      { "category": "food", "difficulty": "medium" }
      """
    Then the response status is 201
    And the response body has "wrong_guesses_allowed" equal to "6"
    And the response body field "word" is absent

  @failure
  Scenario: Unknown category is rejected
    When I POST to "/api/v1/games" with body:
      """
      { "category": "nonexistent", "difficulty": "easy" }
      """
    Then the response status is 422
    And the response error code is "UNKNOWN_CATEGORY"

  @edge
  Scenario: Starting a second game forfeits the first
    Given I start a new game with category "animals" and difficulty "easy"
    When I POST to "/api/v1/games" with body:
      """
      { "category": "tech", "difficulty": "hard" }
      """
    Then the response status is 201
    And the response body has "state" equal to "IN_PROGRESS"
    And the response body has "difficulty" equal to "hard"
