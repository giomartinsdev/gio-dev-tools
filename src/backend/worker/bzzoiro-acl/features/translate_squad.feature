Feature: Squad translation
  As the bzzoiro anti-corruption layer
  I want /api/v2/teams/{id}/squad/ payloads translated without crashing
  So that a team's squad list update doesn't break polling because of
  optional fields the real endpoint never sends

  Background:
    Given a fresh translator

  Scenario: A squad item with only the fields the real endpoint sends is translated
    Given a squad payload for team 159 with a minimal player entry
    When I translate the squad
    Then the squad member has status "active", club "" and club_country ""
    And the squad member's player_id is resolved from the player's own provider id

  Scenario: A squad item with the richer optional fields still maps them
    Given a squad payload for team 159 with a fully populated player entry
    When I translate the squad
    Then the squad member has status "official", club "Club X" and club_country "Brazil"
