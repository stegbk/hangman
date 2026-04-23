Feature: UC4 — Mid-game reload restores the in-progress game

  The session cookie persists the player's active game server-side. After
  reloading the browser, the UI must rehydrate the same game, showing the
  masked word and which letters were already guessed.

  @happy
  Scenario: Reload mid-game keeps the active game and prior guess
    Given the backend and frontend are running
    And I open the app
    And I select category "animals"
    And I select difficulty "easy"
    When I click the "start-game-btn" button
    And I click the keyboard letter "c"
    And I reload the page
    Then I see the score panel
    And the masked word shows "c _ _"
    And the keyboard letter "c" is disabled
