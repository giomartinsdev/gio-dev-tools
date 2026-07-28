Feature: Worker startup and background consumer lifecycle

  Scenario: _init succeeds with working secrets and DB
    When _init runs with working secrets and DB
    Then app state is populated and init_done is set with no error

  Scenario: _init fails when the secret manager fails
    When _init runs with a secret manager that fails
    Then app state has an init error and init_done is set

  Scenario: _run_background does nothing when init already failed
    When _run_background runs with an init error already set
    Then the consumer was never started

  Scenario: _run_background starts the consumer once ready
    When _run_background runs with a working init
    Then the sender was created and the consumer was started

  Scenario: the lifespan context starts and tears down the background task
    When the lifespan context runs a full startup and shutdown cycle
    Then the background task was cancelled
