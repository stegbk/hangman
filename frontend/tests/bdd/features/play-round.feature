Feature: UC1 — Play a round to completion through the UI

  The happy-path fullstack flow: open the app, pick a category + difficulty,
  guess the word correctly, see the win banner, score panel updates,
  history records the game.

  @happy @smoke
  Scenario: Player guesses "cat" on animals/easy and wins
    Given the backend and frontend are running
    And I open the app
    When I select category "animals"
    And I select difficulty "easy"
    And I click the "start-game-btn" button
    And I click the keyboard letter "c"
    And I click the keyboard letter "a"
    And I click the keyboard letter "t"
    Then I see the game-won banner
    And the total score is "70"
    And the current streak is "1"
    And history contains 1 item
