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
