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

  Scenario: fetch_odds paginates a v2 flat array across two full pages
    Given a bzzoiro v2 API that returns 2 full pages of odds
    When I fetch odds from the client
    Then all odds rows across both pages are returned

  Scenario: fetch_odds stops after a partial page
    Given a bzzoiro v2 API that returns 1 partial page of odds
    When I fetch odds from the client
    Then only the partial page of odds is returned

  Scenario: fetch_odds treats a 404 as an empty list
    Given a bzzoiro API that returns 404
    When I fetch odds from the client
    Then an empty list is returned

  Scenario: fetch_predictions paginates a v2 flat array
    Given a bzzoiro v2 API that returns 1 page of predictions
    When I fetch predictions from the client
    Then all prediction rows are returned

  Scenario: fetch_odds paginates the real {count,next,results} envelope
    Given a bzzoiro v2 API that returns 2 enveloped pages of odds
    When I fetch odds from the client
    Then all odds rows across both pages are returned

  Scenario: fetch_predictions also accepts the enveloped shape
    Given a bzzoiro v2 API that returns 1 enveloped page of predictions
    When I fetch predictions from the client
    Then all prediction rows are returned

  # ── New: transient error handling (ReadTimeout / 502) ────────────────────────

  Scenario: A 502 is retried and eventually succeeds (positive)
    Given a bzzoiro API that returns 502 once then succeeds with one odds row
    When I fetch odds from the client
    Then only one odds row is returned without error

  Scenario: Repeated ReadTimeouts exhaust retries and raise an error (negative)
    Given a bzzoiro API that always raises ReadTimeout
    When I fetch odds from the client
    Then a BzzoiroTransientError is raised
