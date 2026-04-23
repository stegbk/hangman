Feature: UC3 + UC3b — Forfeit an in-progress game, but not a terminal one

  UC3: starting a new game while one is IN_PROGRESS must show a confirm
  dialog (the user is about to forfeit). On OK, the backend auto-forfeits
  the previous game and starts a fresh one.

  UC3b: after a game has already reached a terminal state (WON / LOST),
  clicking Start Game must NOT show a forfeit confirm — there's nothing
  active to forfeit. This is the bug caught in Phase 5.1 of the scaffold.

  @happy @smoke @dialog-accept
  Scenario: Starting a new game mid-play prompts forfeit confirm and starts fresh
    Given the backend and frontend are running
    And I open the app
    And I select category "animals"
    And I select difficulty "easy"
    When I click the "start-game-btn" button
    And I click the keyboard letter "c"
    # Prior game now has guessed_letters="c" and masked_word="c__".
    And I click the "start-game-btn" button
    # The @dialog-accept hook clicked OK on the window.confirm dialog.
    Then a dialog has fired
    # Fresh game rehydrated: masked word is back to three underscores and
    # 'c' is no longer marked as already-guessed on the keyboard.
    And the masked word shows "_ _ _"
    And the keyboard letter "c" is enabled

  @happy @smoke @dialog-tracked
  Scenario: Starting a new game after a loss does not prompt forfeit confirm
    Given the backend and frontend are running
    And I open the app
    And I select category "animals"
    And I select difficulty "hard"
    When I click the "start-game-btn" button
    And I click the keyboard letter "b"
    And I click the keyboard letter "d"
    And I click the keyboard letter "e"
    And I click the keyboard letter "f"
    Then I see the game-lost banner
    When I click the "start-game-btn" button
    # No forfeit confirm because the prior game was already LOST (terminal).
    Then no dialog has fired
    # Fresh game rehydrated: banner is gone, masked_word reset.
    And the masked word shows "_ _ _"
