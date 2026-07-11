Feature: Report generation
  As the value_bets_report worker
  I want to fetch, filter, format, and deliver the report on trigger
  So that every active recipient gets tomorrow's value bets on WhatsApp

  Scenario: sends the formatted report to every active recipient
    Given the value bets client returns 1 bet for tomorrow
    And 2 active recipients and 1 inactive recipient
    When the report generator runs
    Then a whatsapp message was published to each active recipient

  Scenario: sends nothing when there are no active recipients
    Given the value bets client returns 1 bet for tomorrow
    And no active recipients
    When the report generator runs
    Then no whatsapp message was published

  Scenario: still runs when no value bets fall on the reference day
    Given the value bets client returns 1 bet for the day after tomorrow
    And 1 active recipient
    When the report generator runs
    Then a whatsapp message was published to each active recipient
