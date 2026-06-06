Feature: Delete asset

  Background:
    Given an empty asset repository
    And an asset with name "FII XPLG11" type "FII" institution "XP" quantity "50" price "100.00" exists

  Scenario: Delete an existing asset
    When I delete the asset
    Then the asset repository is empty
    And an AssetDeleted event is published

  Scenario: Delete a non-existent asset returns false
    When I delete asset "non-existent-id"
    Then the deletion returns false
