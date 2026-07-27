Feature: Rio SPPO/BRT GPS client
  As the bus-tracker-poller worker
  I want pagination-free fetching, transient-error backoff and row parsing to work correctly
  So that a slow/flaky upstream or a malformed row doesn't break polling

  Scenario: fetch_sppo_positions returns every row from a single page
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

  Scenario: A well-formed SPPO row is parsed into typed fields
    Given a well-formed SPPO row
    When I parse the row
    Then the parsed position has line_code "606" and vehicle_id "B25611"

  Scenario: A malformed SPPO row raises ValueError
    Given a SPPO row missing the latitude field
    When I parse the row
    Then a ValueError is raised for the malformed row

  Scenario: fetch_brt_positions returns every vehicle from the live snapshot
    Given the BRT feed returns 200 with 2 vehicles
    When I fetch BRT positions from the client
    Then both BRT vehicles are returned

  Scenario: A well-formed BRT row is parsed into typed fields
    Given a well-formed BRT row
    When I parse the BRT row
    Then the parsed BRT position has line_code "22" and vehicle_id "901008"

  Scenario: A malformed BRT row raises ValueError
    Given a BRT row missing the codigo field
    When I parse the BRT row
    Then a ValueError is raised for the malformed BRT row

  Scenario: fetch_vehicle_colors returns the operator color map
    Given the vehicle colors endpoint returns 2 entries
    When I fetch vehicle colors from the client
    Then the color map has 2 entries

  Scenario: fetch_vehicle_colors degrades to an empty map on failure
    Given the vehicle colors endpoint is unreachable
    When I fetch vehicle colors from the client
    Then the color map is empty
