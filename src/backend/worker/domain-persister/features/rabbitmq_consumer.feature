Feature: RabbitMQ consumers
  As the domain-persister
  I want both consumer loops to ack good messages, nack poison ones, and
  reconnect after a broker error
  So that a bad payload or a dropped connection never stops ingestion

  Scenario: The raw consumer appends a good message and nacks a poison one
    Given a fake broker with one good raw message and one poison raw message
    When the archive-raw consumer runs one connection cycle
    Then the good message was appended and acked
    And the poison message was nacked without requeue

  Scenario: The raw consumer reconnects after a connection error
    Given a fake broker that fails to connect once
    When the archive-raw consumer runs one connection cycle
    Then the connection was retried after the reconnect delay

  Scenario: The persister consumer projects a good message and nacks a poison one
    Given a fake broker with one good domain message and one poison domain message
    When the persister consumer runs one connection cycle
    Then the good message was projected and acked
    And the poison message was nacked without requeue

  Scenario: run_consumers drives both loops concurrently
    Given a fake broker with one good raw message and one good domain message
    When run_consumers executes one cycle of both loops
    Then both queues were consumed
