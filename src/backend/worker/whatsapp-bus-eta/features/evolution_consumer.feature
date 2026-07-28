Feature: Consume messages.upsert events from the Evolution exchange

  Scenario: A good message is handled and acked, an unparseable one is discarded
    Given a fake broker with one good message and one poison message
    When the evolution consumer runs one connection cycle
    Then the good message was handled and acked
    And the poison message was discarded without being handled

  Scenario: A connection failure triggers a reconnect delay
    Given a fake broker that fails to connect once
    When the evolution consumer runs one connection cycle
    Then the connection was retried after the reconnect delay
