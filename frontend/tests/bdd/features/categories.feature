Feature: GET /api/v1/categories

  The categories endpoint returns the list of word-category names and
  difficulty options available for the player to pick from. Under the BDD
  test-mode pool the category set is exactly {animals, food, tech}; the
  difficulty set is {easy, medium, hard} regardless of pool.

  Background:
    Given the backend and frontend are running

  @happy @smoke
  Scenario: Returns the list of categories
    When I request "/api/v1/categories"
    Then the response status is 200
    And the response body array "categories" has length 3

  @happy
  Scenario: Response exposes categories and difficulties
    When I request "/api/v1/categories"
    Then the response status is 200
    And the response body has "categories.0" equal to "animals"
    And the response body has "categories.1" equal to "food"
    And the response body has "categories.2" equal to "tech"
    And the response body array "difficulties" has length 3

  @edge
  Scenario: Categories are returned in stable alphabetical order
    When I request "/api/v1/categories"
    Then the response status is 200
    And the response body has "categories.0" equal to "animals"
    And the response body has "categories.1" equal to "food"
    And the response body has "categories.2" equal to "tech"
