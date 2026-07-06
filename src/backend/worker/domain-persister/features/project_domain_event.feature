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
    And the value bet outcome resolver resolved the match

  Scenario: OddsSnapshotCaptured projects into insert_odds_snapshot
    When an OddsSnapshotCaptured event is processed
    Then insert_odds_snapshot was called

  Scenario: TeamUpdated projects into upsert_team
    When a TeamUpdated event is processed
    Then upsert_team was called

  Scenario: SquadUpdated projects into upsert_squad
    When a SquadUpdated event is processed
    Then upsert_squad was called

  Scenario: OddsComparisonCaptured projects into upsert_odds_comparison and triggers value-bet evaluation
    When an OddsComparisonCaptured event is processed
    Then upsert_odds_comparison was called
    And the value bet detector evaluated the match after odds comparison

  Scenario: PolymarketSnapshotCaptured projects into upsert_polymarket_snapshot
    When a PolymarketSnapshotCaptured event is processed
    Then upsert_polymarket_snapshot was called
    And the value bet detector was not called

  Scenario: OddsBestCaptured merges into odds_comparisons and triggers value-bet evaluation
    When an OddsBestCaptured event is processed
    Then merge_odds_comparison_markets was called
    And the value bet detector evaluated the match after odds comparison

  Scenario: LineupsCaptured projects into upsert_lineups and triggers value-bet evaluation
    When a LineupsCaptured event is processed
    Then upsert_lineups was called
    And the value bet detector evaluated the match after odds comparison

  Scenario: H2HCaptured projects into upsert_h2h without triggering value-bet evaluation
    When a H2HCaptured event is processed
    Then upsert_h2h was called
    And the value bet detector was not called

  Scenario: StandingsCaptured projects into upsert_standings without triggering value-bet evaluation
    When a StandingsCaptured event is processed
    Then upsert_standings was called
    And the value bet detector was not called

  Scenario: An event type outside the known union is logged and skipped
    When an object of an unknown event type is projected directly
    Then no read-model method is called and no exception is raised

  Scenario: VenueCaptured projects into upsert_venue
    When a VenueCaptured event is processed
    Then upsert_venue was called

  Scenario: RefereeCaptured projects into upsert_referee
    When a RefereeCaptured event is processed
    Then upsert_referee was called

  Scenario: PlayerStatsCaptured projects into upsert_player_stats
    When a PlayerStatsCaptured event is processed
    Then upsert_player_stats was called

  Scenario: IncidentsCaptured projects into upsert_incidents
    When an IncidentsCaptured event is processed
    Then upsert_incidents was called

  Scenario: A bug in outcome resolution does not poison an otherwise valid MatchFinished message
    Given the value bet outcome resolver raises on resolve_match
    When a MatchFinished event is processed
    Then upsert_match_finished was called
    And no exception escaped handle
