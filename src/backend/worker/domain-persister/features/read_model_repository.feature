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
