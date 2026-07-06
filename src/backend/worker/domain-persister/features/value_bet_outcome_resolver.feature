Feature: Value bet outcome resolution
  As the domain-persister
  I want to know whether a detected edge actually paid off once the match finishes
  So that "did this strategy make money" has a real answer, not just detection

  Background:
    Given a fresh value bet outcome resolver

  Scenario: No open value bets means nothing is archived
    Given the match has no open value bets
    When the match finishes 2-1
    Then no value bet outcome is archived

  Scenario: A winning 1x2 HOME bet is archived as won
    Given an open value bet for "1x2" "HOME"
    When the match finishes 2-1
    Then the value bet outcome for "1x2" "HOME" is archived as won
    And the value bet for "1x2" "HOME" is no longer open

  Scenario: A losing 1x2 HOME bet is archived as lost
    Given an open value bet for "1x2" "HOME"
    When the match finishes 1-2
    Then the value bet outcome for "1x2" "HOME" is archived as lost

  Scenario: A 1x2 DRAW bet wins only on a draw
    Given an open value bet for "1x2" "DRAW"
    When the match finishes 1-1
    Then the value bet outcome for "1x2" "DRAW" is archived as won

  Scenario: A 1x2 AWAY bet wins when the away side scores more
    Given an open value bet for "1x2" "AWAY"
    When the match finishes 0-1
    Then the value bet outcome for "1x2" "AWAY" is archived as won

  Scenario: An over_under_25 over bet wins when total goals exceed the line
    Given an open value bet for "over_under_25" "over"
    When the match finishes 2-1
    Then the value bet outcome for "over_under_25" "over" is archived as won

  Scenario: An over_under_25 over bet loses when total goals are below the line
    Given an open value bet for "over_under_25" "over"
    When the match finishes 1-0
    Then the value bet outcome for "over_under_25" "over" is archived as lost

  Scenario: A btts yes bet wins when both sides score
    Given an open value bet for "btts" "yes"
    When the match finishes 1-1
    Then the value bet outcome for "btts" "yes" is archived as won

  Scenario: A btts yes bet loses when one side is shut out
    Given an open value bet for "btts" "yes"
    When the match finishes 1-0
    Then the value bet outcome for "btts" "yes" is archived as lost
