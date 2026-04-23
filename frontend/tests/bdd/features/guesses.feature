Feature: POST /api/v1/games/{id}/guesses

  Submits a letter guess. Correct letters appear in guessed_letters and
  reveal positions in masked_word; misses decrement lives_remaining. All
  domain violations (re-guessing, terminal game, malformed letter) return
  specific error codes via the backend's HangmanError envelope.

  Background:
    Given the backend and frontend are running
    And I start a new game with category "animals" and difficulty "easy"

  @happy @smoke
  Scenario: Correct letter reveals positions in masked_word
    When I POST to the current game's guesses endpoint with body:
      """
      { "letter": "c" }
      """
    Then the response status is 200
    And the response body has "state" equal to "IN_PROGRESS"
    And the response body has "guessed_letters" equal to "c"
    And the response body has "masked_word" equal to "c__"
    And the response body has "lives_remaining" equal to "8"

  @happy
  Scenario: Incorrect letter decrements lives
    When I POST to the current game's guesses endpoint with body:
      """
      { "letter": "z" }
      """
    Then the response status is 200
    And the response body has "guessed_letters" equal to "z"
    And the response body has "lives_remaining" equal to "7"

  @failure
  Scenario: Re-guessing the same letter is rejected
    When I POST to the current game's guesses endpoint with body:
      """
      { "letter": "c" }
      """
    Then the response status is 200
    When I POST to the current game's guesses endpoint with body:
      """
      { "letter": "c" }
      """
    Then the response status is 422
    And the response error code is "ALREADY_GUESSED"

  @failure
  Scenario: Guessing after terminal state is rejected
    When I guess the letter "c"
    And I guess the letter "a"
    And I guess the letter "t"
    And I POST to the current game's guesses endpoint with body:
      """
      { "letter": "b" }
      """
    Then the response status is 409
    And the response error code is "GAME_ALREADY_FINISHED"

  @edge
  Scenario: Multi-character letter is rejected by domain validation
    When I POST to the current game's guesses endpoint with body:
      """
      { "letter": "ab" }
      """
    Then the response status is 422
    And the response error code is "INVALID_LETTER"
