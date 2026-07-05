Feature: Event store repository
  As the domain-persister
  I want append() to report whether a raw event_id was newly recorded
  So that the raw consumer can rely on it for idempotency

  Background:
    Given a fake transaction manager for the event store repository

  Scenario: A new event_id is reported as newly recorded
    Given the session reports 1 row affected
    When I append an event to the store
    Then append reports True

  Scenario: A duplicate event_id is reported as not newly recorded
    Given the session reports 0 rows affected
    When I append an event to the store
    Then append reports False
