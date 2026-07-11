Feature: Realtime high-edge alerts
  As the value_bets_report worker
  I want to instantly alert opted-in recipients about very high edge value bets
  So that they don't have to wait for the daily batch to act on the best opportunities

  Scenario: sends an alert for a new value bet above the threshold
    Given realtime alerts enabled with threshold "0.2000"
    And 1 realtime subscriber
    And the value bets client returns 1 value bet with edge "0.25" not yet alerted
    When the realtime alert checker runs one check
    Then a realtime alert was published to the subscriber
    And the value bet was marked as alerted

  Scenario: does not re-alert an already-alerted value bet
    Given realtime alerts enabled with threshold "0.2000"
    And 1 realtime subscriber
    And the value bets client returns 1 value bet with edge "0.25" already alerted
    When the realtime alert checker runs one check
    Then no realtime alert was published

  Scenario: skips value bets below the threshold
    Given realtime alerts enabled with threshold "0.2000"
    And 1 realtime subscriber
    And the value bets client returns 1 value bet with edge "0.10" not yet alerted
    When the realtime alert checker runs one check
    Then no realtime alert was published

  Scenario: does nothing when realtime alerts are disabled
    Given realtime alerts disabled
    And 1 realtime subscriber
    And the value bets client returns 1 value bet with edge "0.25" not yet alerted
    When the realtime alert checker runs one check
    Then no realtime alert was published

  Scenario: does nothing when there are no realtime subscribers
    Given realtime alerts enabled with threshold "0.2000"
    And no realtime subscribers
    And the value bets client returns 1 value bet with edge "0.25" not yet alerted
    When the realtime alert checker runs one check
    Then no realtime alert was published
