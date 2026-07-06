Feature: Insight projection, persistence and query
  As the domain-persister
  I want InsightGenerated events projected into an insights read model and
  queryable via the API
  So that ML predictions survive redelivery and are visible per match

  Scenario: ProjectInsightHandler validates and inserts an insight
    Given a fresh insight projector with a mocked read model repository
    When an InsightGenerated event is processed
    Then insert_insight was called with the event's fields
    And the value bet detector evaluated the match

  Scenario: insert_insight writes to the insights table
    Given a fake transaction manager for the read model repository
    When I insert an insight
    Then the session executed a statement against "insights"

  Scenario: find_insights filters by match_id when given
    Given a fake transaction manager for the read model repository
    And the session query returns 1 insight row
    When I list insights for match "abc-123"
    Then 1 insight dict is returned

  Scenario: ListInsightsHandler delegates to find_insights with paging
    Given a fake read model repository for insights
    When I list insights with limit 10 and offset 5
    Then find_insights was called with match_id None limit 10 and offset 5

  Scenario: ListValueBetsHandler delegates to find_value_bets with paging
    Given a fake read model repository for value bets
    When I list value bets with limit 10 and offset 5
    Then find_value_bets was called with match_id None limit 10 and offset 5

  Scenario: ListValueBetOutcomesHandler delegates to find_value_bet_outcomes with paging
    Given a fake read model repository for value bet outcomes
    When I list value bet outcomes with limit 10 and offset 5
    Then find_value_bet_outcomes was called with match_id None limit 10 and offset 5

  Scenario: SummarizeValueBetOutcomesHandler delegates to summarize_value_bet_outcomes
    Given a fake read model repository for value bet outcomes
    When I summarize value bet outcomes via the handler
    Then summarize_value_bet_outcomes was called
