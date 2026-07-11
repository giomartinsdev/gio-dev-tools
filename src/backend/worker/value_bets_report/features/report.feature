Feature: Report domain logic
  As the value_bets_report worker
  I want to filter, group, and format value bets into a WhatsApp text
  So that recipients get a clear daily summary of tomorrow's opportunities

  Scenario: filters value bets to only the reference day
    Given value bets on "2026-07-11" and "2026-07-12"
    When I filter by reference day "2026-07-12"
    Then only the "2026-07-12" value bets remain

  Scenario: groups filtered value bets by match
    Given 2 value bets for match "m1" and 1 value bet for match "m2"
    When I group value bets by match
    Then there are 2 groups
    And group "m1" has 2 value bets

  Scenario: formats a report with grouped matches and edge percentages
    Given 1 value bet for match "m1" with market "1x2", outcome "HOME", edge "0.164"
    When I format the report for "2026-07-12"
    Then the report contains "Resultado final"
    And the report contains "Casa"
    And the report contains "16.4%"

  Scenario: formats an empty-day message when there are no value bets
    Given no value bets
    When I format the report for "2026-07-12"
    Then the report contains "Nenhuma oportunidade"
