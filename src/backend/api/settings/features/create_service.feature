Feature: Create service

  Scenario: Register a new service
    Given an empty service repository
    When I create a service named "bzzoiro" category "API" secret ref "BZZOIRO_API_KEY"
    Then the service is saved with name "bzzoiro" and category "API"
    And a ServiceCreated event is published

  Scenario: Service name cannot be empty
    Given an empty service repository
    When I try to create a service named "" category "API" status "disconnected"
    Then a validation error contains "name is required"

  Scenario: Invalid category is rejected
    Given an empty service repository
    When I try to create a service named "bzzoiro" category "unknown" status "disconnected"
    Then a validation error contains "Invalid category"

  Scenario: Invalid status is rejected
    Given an empty service repository
    When I try to create a service named "bzzoiro" category "API" status "unknown"
    Then a validation error contains "Invalid status"
