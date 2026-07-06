Feature: Poll command handlers
  As the bzzoiro anti-corruption layer
  I want each poll to fetch, translate and publish in one pass
  So that fixtures/live data flows end-to-end without a real network or broker

  Background:
    Given a fake client, translator and publisher

  Scenario: Polling fixtures publishes the raw payload and its translated events
    Given the fake client returns 1 fixture payload
    When I run the fixtures poll handler
    Then 1 event was polled
    And the publisher recorded a raw publish and at least one domain event publish

  Scenario: Polling fixtures with no results publishes nothing
    Given the fake client returns no fixtures
    When I run the fixtures poll handler
    Then 0 events were polled
    And the publisher recorded no raw publish

  Scenario: Polling live publishes the raw payload and its translated events
    Given the fake client returns 1 live payload
    When I run the live poll handler
    Then 1 event was polled
    And the publisher recorded a raw publish and at least one domain event publish

  Scenario: Polling odds publishes the raw rows and a grouped snapshot event
    Given the fake client returns 3 odds rows for the same event/bookmaker/market
    When I run the odds poll handler
    Then 3 events were polled
    And the publisher recorded a raw publish and at least one domain event publish

  Scenario: Polling odds with no rows publishes nothing
    Given the fake client returns no odds rows
    When I run the odds poll handler
    Then 0 events were polled
    And the publisher recorded no raw publish

  Scenario: Polling predictions publishes the raw payload and an insight
    Given the fake client returns 1 prediction payload
    When I run the predictions poll handler
    Then 1 event was polled
    And the publisher recorded a raw publish and at least one insight publish

  # ── Odds checkpoint contract ──────────────────────────────────────────────────

  Scenario: Polling odds persists the most recent updated_at as its own checkpoint
    Given the fake client returns 3 odds rows for the same event/bookmaker/market
    When I run the odds poll handler
    Then the odds checkpoint is 2026-08-01T10:00:02+00:00

  Scenario: Polling odds with no rows leaves the checkpoint untouched
    Given the fake client returns no odds rows
    When I run the odds poll handler
    Then the odds checkpoint is None

  Scenario: Polling odds honors an existing checkpoint as updated_after
    Given an odds checkpoint of "2026-08-01T09:00:00+00:00" already exists
    And the fake client returns 3 odds rows for the same event/bookmaker/market
    When I run the odds poll handler
    Then fetch_odds_page was called with updated_after 2026-08-01T09:00:00+00:00

  Scenario: Forcing an odds poll ignores the existing checkpoint
    Given an odds checkpoint of "2026-08-01T09:00:00+00:00" already exists
    And the fake client returns 3 odds rows for the same event/bookmaker/market
    When I run the odds poll handler with force
    Then fetch_odds_page was called with updated_after None

  # ── Teams poll + skip-if-recent contract ─────────────────────────────────────

  Scenario: Polling teams publishes the raw payload
    Given the fake client returns 1 team payload
    When I run the teams poll handler
    Then 1 event was polled
    And the publisher recorded a raw publish
    And a teams checkpoint was recorded

  Scenario: Polling teams with no results publishes nothing
    Given the fake client returns no teams
    When I run the teams poll handler
    Then 0 events were polled
    And the publisher recorded no raw publish

  Scenario: Polling teams skips the crawl if synced recently
    Given a teams checkpoint from 60 seconds ago exists
    And the fake client returns 1 team payload
    When I run the teams poll handler
    Then 0 events were polled
    And fetch_teams was not called

  Scenario: Forcing a teams poll bypasses the recent-checkpoint skip
    Given a teams checkpoint from 60 seconds ago exists
    And the fake client returns 1 team payload
    When I run the teams poll handler with force
    Then 1 event was polled
    And fetch_teams was called

  Scenario: Polling odds comparison publishes comparison and polymarket data for events that have it
    Given the fake client returns 1 fixture in the date window with odds comparison and polymarket data
    When I run the odds comparison poll handler
    Then 1 event was polled
    And the publisher recorded a raw publish for "odds_comparison" and a raw publish for "polymarket"

  Scenario: Polling odds comparison skips events bzzoiro has no odds for
    Given the fake client returns 1 fixture in the date window with no odds comparison or polymarket data
    When I run the odds comparison poll handler
    Then 0 events were polled
    And the publisher recorded no raw publish

  Scenario: A transient failure on one event does not abort the rest of the odds comparison poll
    Given the fake client returns 2 fixtures in the date window, one of which always raises on odds comparison
    When I run the odds comparison poll handler
    Then 1 event was polled
    And the publisher recorded a raw publish for "odds_comparison" and a raw publish for "polymarket"
