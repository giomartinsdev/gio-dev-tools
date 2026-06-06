Feature: Create asset

  Scenario: Create a valid asset
    Given an empty asset repository
    When I create an asset with name "Tesouro IPCA+" type "Treasury" institution "BTG" quantity "10" price "1050.00"
    Then the asset is saved with name "Tesouro IPCA+" and type "Treasury"
    And the total value is "10500.00"
    And an AssetCreated event is published

  Scenario: Asset name cannot be empty
    Given an empty asset repository
    When I try to create an asset with name "" type "CDB" institution "Nubank" quantity "1" price "1000.00"
    Then a validation error contains "name is required"

  Scenario: Institution cannot be empty
    Given an empty asset repository
    When I try to create an asset with name "FII XP" type "FII" institution "" quantity "100" price "11.50"
    Then a validation error contains "institution is required"

  Scenario: Invalid asset type is rejected
    Given an empty asset repository
    When I try to create an asset with name "BTC" type "unknown" institution "Binance" quantity "0.5" price "200000.00"
    Then a validation error contains "Invalid type"

  Scenario: Quantity must be positive
    Given an empty asset repository
    When I try to create an asset with name "Stock" type "Stock" institution "XP" quantity "0" price "50.00"
    Then a validation error contains "positive"

  Scenario: Purchase price cannot be negative
    Given an empty asset repository
    When I try to create an asset with name "Stock" type "Stock" institution "XP" quantity "1" price "-10.00"
    Then a validation error contains "negative"
