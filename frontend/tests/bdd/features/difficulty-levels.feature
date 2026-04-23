Feature: Per-difficulty WIN and LOSS mistake counts

  Exercises the lives_total contract across all three difficulty levels in
  the UI. Under the test-mode pool ("cat" in every category), WIN is always
  3 correct guesses (c, a, t) and LOSS is exactly N non-cat misses where
  N = lives_total for the chosen difficulty (8 easy / 6 medium / 4 hard).

  Background:
    Given the backend and frontend are running
    And I open the app
    And I select category "animals"

  @happy
  Scenario: Easy WIN
    When I select difficulty "easy"
    And I click the "start-game-btn" button
    And I click the keyboard letter "c"
    And I click the keyboard letter "a"
    And I click the keyboard letter "t"
    Then I see the game-won banner

  @happy
  Scenario: Easy LOSS after 8 misses
    When I select difficulty "easy"
    And I click the "start-game-btn" button
    And I click the keyboard letter "b"
    And I click the keyboard letter "d"
    And I click the keyboard letter "e"
    And I click the keyboard letter "f"
    And I click the keyboard letter "g"
    And I click the keyboard letter "h"
    And I click the keyboard letter "i"
    And I click the keyboard letter "j"
    Then I see the game-lost banner

  @happy
  Scenario: Medium WIN
    When I select difficulty "medium"
    And I click the "start-game-btn" button
    And I click the keyboard letter "c"
    And I click the keyboard letter "a"
    And I click the keyboard letter "t"
    Then I see the game-won banner

  @happy
  Scenario: Medium LOSS after 6 misses
    When I select difficulty "medium"
    And I click the "start-game-btn" button
    And I click the keyboard letter "b"
    And I click the keyboard letter "d"
    And I click the keyboard letter "e"
    And I click the keyboard letter "f"
    And I click the keyboard letter "g"
    And I click the keyboard letter "h"
    Then I see the game-lost banner

  @happy @smoke
  Scenario: Hard WIN
    When I select difficulty "hard"
    And I click the "start-game-btn" button
    And I click the keyboard letter "c"
    And I click the keyboard letter "a"
    And I click the keyboard letter "t"
    Then I see the game-won banner

  @happy
  Scenario: Hard LOSS after 4 misses
    When I select difficulty "hard"
    And I click the "start-game-btn" button
    And I click the keyboard letter "b"
    And I click the keyboard letter "d"
    And I click the keyboard letter "e"
    And I click the keyboard letter "f"
    Then I see the game-lost banner
