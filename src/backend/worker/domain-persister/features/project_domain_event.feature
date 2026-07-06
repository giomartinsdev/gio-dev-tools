Feature: Domain event projection
  As the domain-persister
  I want every canonical domain event type to project into the right read model call
  So that the materialized views stay in sync with everything the ACL emits

  Background:
    Given a fresh persister with a mocked read model repository

  Scenario: MatchScheduled projects into upsert_match_scheduled
    When a MatchScheduled event is processed
    Then upsert_match_scheduled was called

  Scenario: MatchStatusChanged projects into upsert_match_status
    When a MatchStatusChanged event is processed
    Then upsert_match_status was called

  Scenario: MatchFinished projects into upsert_match_finished
    When a MatchFinished event is processed
    Then upsert_match_finished was called

  Scenario: OddsSnapshotCaptured projects into insert_odds_snapshot
    When an OddsSnapshotCaptured event is processed
    Then insert_odds_snapshot was called

  Scenario: TeamUpdated projects into upsert_team
    When a TeamUpdated event is processed
    Then upsert_team was called

  Scenario: SquadUpdated projects into upsert_squad
    When a SquadUpdated event is processed
    Then upsert_squad was called

  Scenario: An event type outside the known union is logged and skipped
    When an object of an unknown event type is projected directly
    Then no read-model method is called and no exception is raised
