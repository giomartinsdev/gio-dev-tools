Feature: Translate bzzoiro payloads into canonical domain events
  As the bzzoiro anti-corruption layer
  I want to translate provider payloads into canonical domain events
  So that downstream consumers never see bzzoiro's own ids or status vocabulary

  Background:
    Given a fresh translator

  Scenario Outline: Map provider status to the canonical enum
    Given a bzzoiro event payload with id "<provider_id>" status "<provider_status>"
    When I translate the payload
    Then a MatchStatusChanged event with status "<canonical_status>" is produced
    And no provider id leaks into the event

    Examples:
      | provider_id | provider_status | canonical_status |
      | 501         | upcoming        | SCHEDULED         |
      | 502         | live            | LIVE              |
      | 503         | finished        | FINISHED          |
      | 504         | postponed       | POSTPONED         |
      | 505         | cancelled       | CANCELLED         |

  Scenario: A real-shaped payload produces a MatchScheduled event with the right ids and kickoff
    Given a bzzoiro event payload with id "601" status "notstarted"
    When I translate the payload
    Then a MatchScheduled event with a kickoff time is produced

  Scenario: Identity resolution is stable across polls
    Given a bzzoiro event payload with id "777" status "live"
    When I translate the payload
    Then the same provider ref resolves to the same canonical match id

  Scenario: A finished match also emits MatchFinished with the final score
    Given a bzzoiro event payload with id "808" status "finished" score home 3 away 1
    When I translate the payload
    Then a MatchFinished event with home score 3 and away score 1 is produced

  Scenario: A dict-shaped status (WebSocket "event" frame shape) is also accepted
    Given a bzzoiro event payload with id "909" and dict-shaped status "live"
    When I translate the payload
    Then a MatchStatusChanged event with status "LIVE" is produced

  Scenario: A payload with no status field at all produces no status event
    Given a bzzoiro event payload with id "910" and no status field at all
    When I translate the payload
    Then no MatchStatusChanged event is produced
