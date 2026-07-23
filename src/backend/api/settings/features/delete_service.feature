Feature: Delete service

  Background:
    Given an empty service repository
    And a service named "domain-persister" category "Worker" exists

  Scenario: Delete an existing service
    When I delete the service
    Then the service repository is empty
    And a ServiceDeleted event is published

  Scenario: Delete a non-existent service returns false
    When I delete service "non-existent-id"
    Then the deletion returns false
