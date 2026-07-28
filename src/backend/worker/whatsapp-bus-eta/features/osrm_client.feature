Feature: Fetch a route duration from OSRM

  Scenario: A successful route returns minutes
    Given OSRM will respond with status 200 and duration 300 seconds
    When I request a "foot" route
    Then the route result is 5.0 minutes

  Scenario: A non-200 response yields no result
    Given OSRM will respond with status 500
    When I request a "car" route
    Then the route result is None

  Scenario: A network error yields no result
    Given OSRM will raise a connection error
    When I request a "car" route
    Then the route result is None
