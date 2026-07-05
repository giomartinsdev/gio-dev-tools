Feature: FastAPI app lifecycle
  As the bzzoiro anti-corruption layer
  I want startup/shutdown and the reconnecting background loop to behave correctly
  So that a broker outage or bad secrets don't crash the process

  Scenario: _init succeeds and populates app state
    When _init runs with working secrets and DB
    Then app state is populated and init_done is set with no error

  Scenario: _init failure is captured instead of raised
    When _init runs with a secret manager that fails
    Then app state has an init error and init_done is set

  Scenario: _poll_loop logs a successful poll and keeps looping
    When _poll_loop runs one successful iteration
    Then the handler was called and the loop continued

  Scenario: _poll_loop logs a failed poll and keeps looping
    When _poll_loop runs one failing iteration
    Then the failure was logged and the loop continued

  Scenario: _run_background exits immediately if init failed
    When _run_background runs with an init error already set
    Then the publisher was never connected

  Scenario: _run_background connects, polls, then reconnects on cancellation
    When _run_background runs through one successful connect-and-poll cycle
    Then the publisher was connected and poll loops were started

  Scenario: _run_background retries after a connection error
    When _run_background hits a connection error on its first attempt
    Then the error was logged and a reconnect was scheduled

  Scenario: lifespan starts and cleanly tears down background work
    When the lifespan context runs a full startup and shutdown cycle
    Then the background task was cancelled and the publisher was closed
