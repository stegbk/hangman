Feature: GET /api/v1/history

  Returns the session's terminal (finalized) games ordered by finished_at
  DESC. Supports pagination via page/page_size.

  Background:
    Given the backend and frontend are running

  @happy @smoke
  Scenario: Finalized games appear in history
    Given I start a new game with category "animals" and difficulty "easy"
    And I guess the letter "c"
    And I guess the letter "a"
    And I guess the letter "t"
    When I request "/api/v1/history"
    Then the response status is 200
    And the response body array "items" has length 1
    And the response body has "items.0.state" equal to "WON"

  @happy
  Scenario: Most recent completion appears first
    Given I start a new game with category "animals" and difficulty "easy"
    And I guess the letter "c"
    And I guess the letter "a"
    And I guess the letter "t"
    And I start a new game with category "food" and difficulty "hard"
    And I guess the letter "b"
    And I guess the letter "d"
    And I guess the letter "e"
    And I guess the letter "f"
    When I request "/api/v1/history"
    Then the response status is 200
    And the response body array "items" has length 2
    And the response body has "items.0.state" equal to "LOST"
    And the response body has "items.1.state" equal to "WON"

  @edge
  Scenario: Empty history returns an empty items array
    When I request "/api/v1/history"
    Then the response status is 200
    And the response body array "items" has length 0

  @edge
  Scenario: Pagination honors page and page_size
    Given I start a new game with category "animals" and difficulty "easy"
    And I guess the letter "c"
    And I guess the letter "a"
    And I guess the letter "t"
    And I start a new game with category "food" and difficulty "easy"
    And I guess the letter "c"
    And I guess the letter "a"
    And I guess the letter "t"
    When I request "/api/v1/history?page=2&page_size=1"
    Then the response status is 200
    And the response body array "items" has length 1
    And the response body has "page" equal to "2"
    And the response body has "page_size" equal to "1"
    And the response body has "total" equal to "2"
