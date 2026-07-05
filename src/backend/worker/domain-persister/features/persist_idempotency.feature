Feature: Idempotent event persistence
  As the domain-persister
  I want redelivered messages to never duplicate state
  So that RabbitMQ's at-least-once delivery is safe to reprocess

  Background:
    Given a fresh persister

  Scenario: Reprocessing the same domain event does not duplicate the read model
    Given a MatchScoreUpdated event for match "arsenal-vs-chelsea" with score 1-0 at minute 34
    When the persister processes that event
    And the persister processes that event again (redelivery)
    Then the match read model shows score 1-0
    And only one match row exists

  Scenario: Reprocessing the same raw event_id does not duplicate the event store
    Given a raw event store record with event_id "11111111-1111-1111-1111-111111111111"
    When the event store appends that event_id twice
    Then only the first append is recorded
