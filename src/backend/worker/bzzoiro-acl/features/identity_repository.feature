Feature: Postgres-backed identity mapping
  As the bzzoiro anti-corruption layer
  I want provider_ref -> canonical_id mappings to be created once and reused
  So that the same bzzoiro entity always resolves to the same internal UUID

  Background:
    Given a fresh provider mapping table

  Scenario: A new provider_ref creates a mapping
    When I resolve provider_ref "42" of type "match" for the first time
    Then a canonical UUID is returned

  Scenario: The same provider_ref resolves to the same canonical id
    Given provider_ref "42" of type "match" was already resolved
    When I resolve provider_ref "42" of type "match" again
    Then the same canonical UUID is returned as before

  Scenario: The same provider_ref but a different entity_type gets a different id
    Given provider_ref "42" of type "match" was already resolved
    When I resolve provider_ref "42" of type "team"
    Then a different canonical UUID is returned
