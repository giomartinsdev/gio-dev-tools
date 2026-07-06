Feature: FastAPI deps and router wiring
  As the domain-persister
  I want the readiness gate and read-model endpoints to behave correctly
  So that callers get a clean 503 until startup finishes and correct query results otherwise

  Scenario: _ready passes once init is done and there is no error
    Given persister app state with init done and no error
    When I call persister _ready
    Then no exception is raised

  Scenario: _ready raises 503 when init failed
    Given persister app state with init done and an init error
    When I call persister _ready expecting an error
    Then a 503 HTTPException is raised

  Scenario: get_read_models returns the state object
    Given persister app state with init done and no error
    When I call get_read_models
    Then it returns the read models object

  Scenario: GET /matches returns the list from the repository
    Given a fake read model repository returning 1 match
    When I call the list_matches endpoint
    Then 1 match is returned

  Scenario: GET /matches/{id} returns the match when found
    Given a fake read model repository with match "abc-123"
    When I call the get_match endpoint for "abc-123"
    Then the match "abc-123" is returned

  Scenario: GET /matches/{id} 404s when not found
    Given a fake read model repository with no matches
    When I call the get_match endpoint for "missing" expecting an error
    Then a 404 HTTPException is raised

  Scenario: GET /insights returns the list from the repository
    Given a fake read model repository returning 1 insight
    When I call the list_insights endpoint
    Then 1 insight is returned
