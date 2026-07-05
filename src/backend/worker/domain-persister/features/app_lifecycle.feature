Feature: FastAPI app lifecycle
  As the domain-persister
  I want startup/shutdown to wire the DB and hand off to the RabbitMQ consumers
  So that bad secrets don't crash the process and shutdown cancels cleanly

  Scenario: _init succeeds and populates app state
    When _init runs with working secrets and DB
    Then app state is populated and init_done is set with no error

  Scenario: _init failure is captured instead of raised
    When _init runs with a secret manager that fails
    Then app state has an init error and init_done is set

  Scenario: _run_background exits immediately if init failed
    When _run_background runs with an init error already set
    Then run_consumers was never called

  Scenario: _run_background hands off to run_consumers once ready
    When _run_background runs with init already done successfully
    Then run_consumers was called with the read models and event store

  Scenario: lifespan starts and cleanly cancels the background task
    When the lifespan context runs a full startup and shutdown cycle
    Then the background task was cancelled
