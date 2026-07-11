Feature: Daily scheduler
  As the value_bets_report worker
  I want to fire a trigger at a configurable time each day
  So that the report goes out automatically without an external cron

  Scenario: computes today's send time when still in the future
    Given the current time is "2026-07-11T10:00:00" in the report timezone
    When I compute the next fire time for send_time "23:00"
    Then the next fire time is "2026-07-11T23:00:00" in the report timezone

  Scenario: computes tomorrow's send time when today's has already passed
    Given the current time is "2026-07-11T23:30:00" in the report timezone
    When I compute the next fire time for send_time "00:00"
    Then the next fire time is "2026-07-12T00:00:00" in the report timezone

  Scenario: publishes a trigger message when the fire time is reached
    Given a scheduler with enabled config and send_time "00:00"
    When the scheduler runs one cycle
    Then a trigger was published with reason "scheduled"

  Scenario: skips firing while disabled, re-checking config periodically
    Given a scheduler with disabled config
    When the scheduler runs one cycle
    Then no trigger was published
