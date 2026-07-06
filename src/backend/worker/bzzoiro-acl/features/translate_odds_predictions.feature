Feature: Translate bzzoiro v2 odds and predictions
  As the bzzoiro anti-corruption layer
  I want /api/v2/odds/ rows and /api/v2/predictions/ payloads translated into
  canonical domain events
  So that odds history and ML predictions flow through the same pipeline as fixtures

  Background:
    Given a fresh translator for odds and predictions

  Scenario: Odds rows for the same event/bookmaker/market are grouped into one snapshot
    Given 3 v2 odds rows for event "42" bookmaker "bet365" market "1x2" with outcomes home=2.10 draw=3.40 away=3.60
    When I translate the odds rows
    Then 1 OddsSnapshotCaptured event is produced with 3 selections

  Scenario: Odds rows for different bookmakers produce separate snapshots
    Given v2 odds rows for event "42" from bookmakers "bet365" and "pinnacle" both market "1x2"
    When I translate the odds rows
    Then 2 OddsSnapshotCaptured events are produced

  Scenario: A v2 prediction is translated into an InsightGenerated event
    Given a v2 prediction payload for event "77" with confidence 0.82 recommending the favorite
    When I translate the prediction
    Then an InsightGenerated event with confidence "0.82" is produced
    And the recommendation mentions the favorite

  Scenario: A v2 prediction with no recommended bets translates to "no_bet"
    Given a v2 prediction payload for event "88" with confidence 0.4 recommending nothing
    When I translate the prediction
    Then the recommendation is "no_bet"

  Scenario: resolve_match_id returns the same id translate_odds_items would use
    Given 3 v2 odds rows for event "42" bookmaker "bet365" market "1x2" with outcomes home=2.10 draw=3.40 away=3.60
    When I translate the odds rows
    And I resolve the match id for provider_ref "42"
    Then the resolved match id matches the snapshot's match id
