Feature: Delete a financial transaction
  As a user
  I want to remove an incorrectly recorded transaction
  So that my records stay accurate

  Background:
    Given an empty transaction repository
    And I have recorded an income of "100.00" in category "Salary" described as "Test entry"

  Scenario: Delete an existing transaction
    When I delete the last recorded transaction
    Then the repository is empty
    And a TransactionDeleted event is published

  Scenario: Deleting a non-existent transaction returns false
    When I delete transaction "non-existent-id"
    Then the deletion returns false
    And no TransactionDeleted event is published
    And 1 transaction is saved
