Feature: Update asset

  Background:
    Given an empty asset repository
    And an asset with name "CDB Nubank" type "CDB" institution "Nubank" quantity "1" price "1000.00" exists

  Scenario: Update creates a new asset (immutable ledger)
    When I update the asset with name "CDB Nubank Plus" type "CDB" institution "Nubank" quantity "2" price "1050.00"
    Then the repository has 1 asset
    And the asset has name "CDB Nubank Plus" and quantity "2"
    And the asset id changed
    And an AssetUpdated event is published

  Scenario: Update non-existent asset returns nothing
    When I update asset "non-existent-id" with name "X" type "CDB" institution "Y" quantity "1" price "1.00"
    Then no update is performed

  Scenario: Update with empty name is rejected
    When I try to update the asset with name "" type "CDB" institution "Nubank" quantity "1" price "1000.00"
    Then a validation error contains "name is required"
