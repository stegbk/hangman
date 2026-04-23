Feature: UC2 — A loss resets the current streak

  After winning a game the streak is 1 (score 70). Starting a second game
  and losing it must reset the current streak to 0 while keeping the total
  score at 70 (losses add zero; wins never decrement).

  @happy
  Scenario: Win then lose — streak resets, score preserved
    Given the backend and frontend are running
    And I open the app
    And I select category "animals"
    And I select difficulty "easy"
    When I click the "start-game-btn" button
    And I click the keyboard letter "c"
    And I click the keyboard letter "a"
    And I click the keyboard letter "t"
    Then I see the game-won banner
    And the total score is "70"
    And the current streak is "1"
    When I select difficulty "hard"
    And I click the "start-game-btn" button
    And I click the keyboard letter "b"
    And I click the keyboard letter "d"
    And I click the keyboard letter "e"
    And I click the keyboard letter "f"
    Then I see the game-lost banner
    And the total score is "70"
    And the current streak is "0"
    And history contains 2 items
