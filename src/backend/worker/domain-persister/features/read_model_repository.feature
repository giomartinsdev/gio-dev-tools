Feature: Read model repository
  As the domain-persister
  I want each upsert to target the right table with the right conflict key
  So that projections land in the correct read model row

  Background:
    Given a fake transaction manager for the read model repository

  Scenario: upsert_match_scheduled writes to the matches table
    When I upsert a scheduled match
    Then the session executed a statement against "matches"

  Scenario: upsert_match_status writes to the matches table
    When I upsert a match status
    Then the session executed a statement against "matches"

  Scenario: upsert_match_score writes to the matches table
    When I upsert a match score
    Then the session executed a statement against "matches"

  Scenario: upsert_match_finished writes to the matches table
    When I upsert a finished match
    Then the session executed a statement against "matches"

  Scenario: insert_odds_snapshot writes to the odds_snapshots table
    When I insert an odds snapshot
    Then the session executed a statement against "odds_snapshots"

  Scenario: find_all_matches maps rows to dicts
    Given the session query returns 1 match row
    When I list all matches
    Then 1 match dict is returned

  Scenario: find_match returns a dict when the row exists
    Given the session get returns a match row
    When I get that match
    Then a match dict is returned

  Scenario: find_match returns None when the row is missing
    Given the session get returns no row
    When I get that match
    Then None is returned

  Scenario: upsert_odds_comparison writes to the odds_comparisons table
    When I upsert an odds comparison
    Then the session executed a statement against "odds_comparisons"

  Scenario: upsert_polymarket_snapshot writes to the polymarket_snapshots table
    When I upsert a polymarket snapshot
    Then the session executed a statement against "polymarket_snapshots"

  Scenario: upsert_value_bet writes to the value_bets table
    When I upsert a value bet
    Then the session executed a statement against "value_bets"

  Scenario: find_odds_comparison returns a dict when the row exists
    Given the session get returns an odds comparison row
    When I get the odds comparison
    Then an odds comparison dict is returned

  Scenario: find_odds_comparison returns None when the row is missing
    Given the session get returns no row
    When I get the odds comparison
    Then None is returned

  Scenario: find_latest_insight returns the most recent insight for a match
    Given the session query returns 1 insight row for find_latest_insight
    When I get the latest insight
    Then an insight dict is returned

  Scenario: find_latest_insight returns None when there is no insight yet
    Given the session query returns no rows for find_latest_insight
    When I get the latest insight
    Then None is returned

  Scenario: find_value_bets maps rows to dicts
    Given the session query returns 1 value bet row
    When I list value bets
    Then 1 value bet dict is returned

  Scenario: delete_value_bet issues a delete against the value_bets table
    When I delete a value bet
    Then a delete was issued against the value_bets table

  Scenario: merge_odds_comparison_markets writes to the odds_comparisons table
    When I merge odds comparison markets
    Then the session executed a statement against "odds_comparisons"

  Scenario: upsert_lineups writes to the lineups table
    When I upsert lineups
    Then the session executed a statement against "lineups"

  Scenario: find_lineups returns a dict when the row exists
    Given the session get returns a lineups row
    When I get the lineups
    Then a lineups dict is returned

  Scenario: find_lineups returns None when the row is missing
    Given the session get returns no row
    When I get the lineups
    Then None is returned

  Scenario: upsert_h2h writes to the h2h table
    When I upsert h2h
    Then the session executed a statement against "h2h"

  Scenario: find_h2h returns a dict when the row exists
    Given the session get returns a h2h row
    When I get the h2h
    Then a h2h dict is returned

  Scenario: upsert_standings writes to the standings table
    When I upsert standings
    Then the session executed a statement against "standings"

  Scenario: find_standings returns a dict when the row exists
    Given the session get returns a standings row
    When I get the standings
    Then a standings dict is returned
