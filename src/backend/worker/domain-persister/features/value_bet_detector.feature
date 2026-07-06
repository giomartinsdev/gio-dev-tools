Feature: Value bet detection
  As the domain-persister
  I want to correlate bzzoiro's own model probability against the best
  market price for the same match
  So that a real edge (model_probability - implied_probability) becomes a
  queryable, actionable record instead of two disconnected facts

  Background:
    Given a fresh value bet detector

  Scenario: No insight yet means no evaluation happens
    Given odds comparison data exists for the match with best odds 2.20 on "1x2" "HOME"
    When the detector evaluates the match
    Then no value bet is recorded

  Scenario: No odds comparison yet means no evaluation happens
    Given an insight exists with match_result prob_home 60
    When the detector evaluates the match
    Then no value bet is recorded

  Scenario: A clear edge above the threshold is recorded
    Given an insight exists with match_result prob_home 60
    And odds comparison data exists for the match with best odds 2.20 on "1x2" "HOME"
    When the detector evaluates the match
    Then a value bet is recorded for "1x2" "HOME" with edge close to 0.1455

  Scenario: No meaningful edge means nothing is recorded
    Given an insight exists with match_result prob_home 45
    And odds comparison data exists for the match with best odds 2.20 on "1x2" "HOME"
    When the detector evaluates the match
    Then no value bet is recorded

  Scenario: An edge that drops back below threshold removes a previously recorded value bet
    Given an insight exists with match_result prob_home 60
    And odds comparison data exists for the match with best odds 2.20 on "1x2" "HOME"
    And the detector already evaluated the match once
    When the odds move to best odds 1.50 on "1x2" "HOME"
    And the detector evaluates the match
    Then no value bet is recorded

  Scenario: A market the odds comparison doesn't cover yet is skipped without error
    Given an insight exists with match_result prob_home 60 and over_under prob_over_25 70
    And odds comparison data exists for the match with best odds 2.20 on "1x2" "HOME"
    When the detector evaluates the match
    Then a value bet is recorded for "1x2" "HOME" with edge close to 0.1455
    And no value bet is recorded for "over_under_25" "over"

  Scenario: Multiple markets are evaluated independently in one pass
    Given an insight exists with match_result prob_home 60 and over_under prob_over_25 70
    And odds comparison data exists for the match with best odds 2.20 on "1x2" "HOME" and best odds 1.65 on "over_under_25" "over"
    When the detector evaluates the match
    Then a value bet is recorded for "1x2" "HOME" with edge close to 0.1455
    And a value bet is recorded for "over_under_25" "over" with edge close to 0.0939

  Scenario: A low-confidence predicted lineup suppresses an otherwise-valid edge
    Given an insight exists with match_result prob_home 60
    And odds comparison data exists for the match with best odds 2.20 on "1x2" "HOME"
    And a predicted lineup exists with confidence 0.4 for both sides
    When the detector evaluates the match
    Then no value bet is recorded

  Scenario: A high-confidence predicted lineup does not block a valid edge
    Given an insight exists with match_result prob_home 60
    And odds comparison data exists for the match with best odds 2.20 on "1x2" "HOME"
    And a predicted lineup exists with confidence 0.8 for both sides
    When the detector evaluates the match
    Then a value bet is recorded for "1x2" "HOME" with edge close to 0.1455

  Scenario: A low-confidence lineup on just one side is still enough to suppress
    Given an insight exists with match_result prob_home 60
    And odds comparison data exists for the match with best odds 2.20 on "1x2" "HOME"
    And a predicted lineup exists with home confidence 0.9 and away confidence 0.3
    When the detector evaluates the match
    Then no value bet is recorded

  Scenario: Real percentage-scale probabilities from bzzoiro's markets block are handled correctly
    Given an insight exists with match_result prob_home 55.5
    And odds comparison data exists for the match with best odds 2.50 on "1x2" "HOME"
    When the detector evaluates the match
    Then a value bet is recorded for "1x2" "HOME" with edge close to 0.155

  Scenario: A brand-new value bet triggers a notification
    Given a fresh value bet detector with a notifier
    And an insight exists with match_result prob_home 60
    And odds comparison data exists for the match with best odds 2.20 on "1x2" "HOME"
    When the detector evaluates the match
    Then the notifier sent an alert

  Scenario: Re-confirming an already-known value bet does not notify again
    Given a fresh value bet detector with a notifier
    And an insight exists with match_result prob_home 60
    And odds comparison data exists for the match with best odds 2.20 on "1x2" "HOME"
    And the detector already evaluated the match once
    When the detector evaluates the match
    Then the notifier was not called again

  Scenario: A failing notifier does not stop the value bet from being recorded
    Given a fresh value bet detector with a notifier that raises on notify
    And an insight exists with match_result prob_home 60
    And odds comparison data exists for the match with best odds 2.20 on "1x2" "HOME"
    When the detector evaluates the match
    Then a value bet is recorded for "1x2" "HOME" with edge close to 0.1455
