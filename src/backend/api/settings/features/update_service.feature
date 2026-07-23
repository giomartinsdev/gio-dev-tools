Feature: Update service

  Background:
    Given an empty service repository
    And a service named "bzzoiro" category "API" exists

  Scenario: Update changes status in place
    When I update the service with name "bzzoiro" category "API" status "connected"
    Then the service repository has 1 service
    And the service has name "bzzoiro" and status "connected"
    And a ServiceUpdated event is published

  Scenario: Update non-existent service returns nothing
    When I update service "non-existent-id" with name "x" category "API" status "connected"
    Then no update is performed

  Scenario: Update with empty name is rejected
    When I try to update the service with name "" category "API" status "connected"
    Then a validation error contains "name is required"
