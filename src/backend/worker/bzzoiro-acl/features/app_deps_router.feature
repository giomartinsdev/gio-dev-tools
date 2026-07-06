Feature: FastAPI deps and router wiring
  As the bzzoiro anti-corruption layer
  I want the readiness gate and manual-trigger endpoints to behave correctly
  So that callers get a clean 503 until startup finishes and clear errors on failure

  Scenario: _ready passes once init is done and there is no error
    Given app state with init done and no error
    When I call _ready
    Then no exception is raised

  Scenario: _ready raises 503 when init failed
    Given app state with init done and an init error
    When I call _ready expecting an error
    Then a 503 HTTPException is raised

  Scenario: get_client, get_translator and get_publisher return the state objects
    Given app state with init done and no error
    When I call the dependency getters
    Then each getter returns the matching state object

  Scenario: POST /poll/fixtures returns the polled count
    Given fake poll dependencies with 1 fixture payload
    When I call the poll_fixtures endpoint
    Then the endpoint returns polled count 1

  Scenario: POST /poll/fixtures surfaces handler errors as a 500
    Given a poll handler that raises an error
    When I call the poll_fixtures endpoint expecting an error
    Then a 500 HTTPException is raised

  Scenario: POST /poll/live returns the polled count
    Given fake poll dependencies with 1 live payload
    When I call the poll_live endpoint
    Then the endpoint returns polled count 1

  Scenario: POST /poll/odds returns the polled count
    Given fake poll dependencies with 1 fixture payload
    When I call the poll_odds endpoint
    Then the endpoint returns polled count 0

  Scenario: POST /poll/predictions returns the polled count
    Given fake poll dependencies with 1 fixture payload
    When I call the poll_predictions endpoint
    Then the endpoint returns polled count 0

  Scenario: POST /poll/odds surfaces handler errors as a 500
    Given a poll handler that raises an error
    When I call the poll_odds endpoint expecting an error
    Then a 500 HTTPException is raised

  Scenario: POST /poll/predictions surfaces handler errors as a 500
    Given a poll handler that raises an error
    When I call the poll_predictions endpoint expecting an error
    Then a 500 HTTPException is raised

  Scenario: POST /poll/teams returns the polled count
    Given fake poll dependencies with 1 fixture payload
    When I call the poll_teams endpoint
    Then the endpoint returns polled count 0

  Scenario: POST /poll/teams surfaces handler errors as a 500
    Given a poll handler that raises an error
    When I call the poll_teams endpoint expecting an error
    Then a 500 HTTPException is raised

  Scenario: POST /resync runs every poller and reports all five feeds
    Given fake poll dependencies with 1 fixture payload
    When I call the resync endpoint
    Then the resync endpoint reports all five feeds

  Scenario: POST /resync surfaces handler errors as a 500
    Given a poll handler that raises an error
    When I call the resync endpoint expecting an error
    Then a 500 HTTPException is raised
