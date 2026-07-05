Feature: Translator edge cases
  As the bzzoiro anti-corruption layer
  I want malformed or empty odds fragments to be skipped instead of crashing
  So that one bad market in a payload doesn't lose the whole translation

  Background:
    Given a fresh translator

  Scenario: A non-dict odds market entry is skipped
    Given a bzzoiro event payload with a malformed odds market "weird"
    When I translate the payload
    Then no OddsSnapshotCaptured event is produced

  Scenario: An odds market with only null prices is skipped
    Given a bzzoiro event payload with odds market "1x2" where every price is null
    When I translate the payload
    Then no OddsSnapshotCaptured event is produced
