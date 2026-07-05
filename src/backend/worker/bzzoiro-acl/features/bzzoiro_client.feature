Feature: bzzoiro REST client
  As the bzzoiro anti-corruption layer
  I want pagination, rate-limit backoff and error handling to work correctly
  So that a slow/rate-limiting/flaky upstream doesn't break polling

  Scenario: Pagination follows next until it is null
    Given a bzzoiro API that returns 2 pages of events
    When I fetch events from the client
    Then all results across both pages are returned

  Scenario: A 429 is retried and eventually succeeds
    Given a bzzoiro API that returns 429 once then succeeds
    When I fetch events from the client
    Then the results from the successful response are returned

  Scenario: A 401 raises an auth error
    Given a bzzoiro API that returns 401
    When I fetch events from the client
    Then a BzzoiroAuthError is raised

  Scenario: A 404 is treated as an empty page
    Given a bzzoiro API that returns 404
    When I fetch events from the client
    Then an empty list is returned

  Scenario: fetch_live paginates the live endpoint
    Given a bzzoiro API that returns 1 page of live events
    When I fetch live events from the client
    Then all results from the live page are returned
