Feature: FastAPI app lifecycle
  As the value_bets_report worker
  I want startup/shutdown to wire the DB and hand off to the scheduler + trigger consumer
  So that bad secrets don't crash the process and shutdown cancels cleanly

  Scenario: _init succeeds and populates app state
    When _init runs with working secrets and DB
    Then app state is populated and init_done is set with no error

  Scenario: _init failure is captured instead of raised
    When _init runs with a secret manager that fails
    Then app state has an init error and init_done is set

  Scenario: _run_background exits immediately if init failed
    When _run_background runs with an init error already set
    Then neither the scheduler nor the trigger consumer were started

  Scenario: _run_background hands off to the scheduler and trigger consumer once ready
    When _run_background runs with init already done successfully
    Then both the scheduler and the trigger consumer were started

  Scenario: lifespan starts and cleanly cancels the background task
    When the lifespan context runs a full startup and shutdown cycle
    Then the background task was cancelled

  Scenario: _ready passes once init is done and there is no error
    Given app state with init done and no error
    When I call _ready
    Then no exception is raised

  Scenario: _ready raises 503 when init failed
    Given app state with init done and an init error
    When I call _ready expecting an error
    Then a 503 HTTPException is raised
