Feature: Rio SPPO GPS client
  As the bus-tracker-poller worker
  I want pagination-free fetching, transient-error backoff and row parsing to work correctly
  So that a slow/flaky upstream or a malformed row doesn't break polling

  Scenario: fetch_positions returns every row from a single page
    Given the SPPO feed returns 200 with 2 rows
    When I fetch positions from the client
    Then all rows are returned

  Scenario: A 502 is retried and eventually succeeds
    Given the SPPO feed returns 502 once then succeeds
    When I fetch positions from the client
    Then the row after retry is returned

  Scenario: Repeated ReadTimeouts exhaust retries and raise an error
    Given the SPPO feed always times out
    When I fetch positions from the client
    Then a RioGpsTransientError is raised

  Scenario: A well-formed row is parsed into typed fields
    Given a well-formed SPPO row
    When I parse the row
    Then the parsed position has line_code "606" and vehicle_id "B25611"

  Scenario: A malformed row raises ValueError
    Given a SPPO row missing the latitude field
    When I parse the row
    Then a ValueError is raised for the malformed row
