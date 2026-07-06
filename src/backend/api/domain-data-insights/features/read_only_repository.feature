Feature: Read-only view over bzzoiro_data
  As domain-data-insights
  I want to query bzzoiro_data (owned by bzzoiro-acl/domain-persister) read-only
  So that a dashboard can plot match, value-bet, and insight data without
  either ACL service needing to expose its own HTTP surface to the gateway

  Scenario: get_overview reports a row per known table
    Given a fake transaction manager returning overview rows
    When I get the overview
    Then 16 overview rows are returned
    And the first overview row has a table name and a row count

  Scenario: find_matches returns matches joined with team names
    Given a fake transaction manager returning 1 match row
    When I list matches with limit 10 and offset 0
    Then 1 match dict is returned
    And the match dict has home and away team names

  Scenario: find_value_bets returns value bets joined with team names
    Given a fake transaction manager returning 1 value bet row
    When I list value bets with limit 10 and offset 0
    Then 1 value bet dict is returned

  Scenario: summarize_value_bet_outcomes reports win rate
    Given a fake transaction manager returning 3 total and 2 won outcomes
    When I summarize value bet outcomes
    Then the summary reports 3 total, 2 won, 1 lost

  Scenario: find_insights returns insights joined with team names
    Given a fake transaction manager returning 1 insight row
    When I list insights with limit 10 and offset 0
    Then 1 insight dict is returned
