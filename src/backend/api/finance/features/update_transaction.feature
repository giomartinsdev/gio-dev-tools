Feature: Update a financial transaction
  As a user
  I want to correct a recorded transaction
  So that my records remain accurate using double-entry accounting

  Background:
    Given an empty transaction repository
    And I have recorded an income of "200.00" in category "Salary" described as "Bonus"

  Scenario: Update creates a reversal and a new corrected entry
    When I update the transaction with amount "250.00" type "income" category "Salary" description "Bonus corrected"
    Then 3 transactions are saved
    And a reversal transaction of "-200.00" exists
    And a new transaction of "250.00" exists

  Scenario: Update can change the transaction type
    When I update the transaction with amount "100.00" type "expense" category "Transfer" description "Moved to savings"
    Then 3 transactions are saved
    And a new transaction of "100.00" with type "expense" exists

  Scenario: Updating a non-existent transaction returns nothing
    When I update transaction "non-existent-id" with amount "100.00" type "income" category "X" description "X"
    Then no update is performed

  Scenario: Amount cannot be zero on update
    When I try to update the transaction with amount "0" type "income" category "Salary" description "Test"
    Then a validation error contains "cannot be zero"

  Scenario: Invalid amount is rejected on update
    When I try to update the transaction with amount "not-a-number" type "income" category "Salary" description "Test"
    Then a validation error contains "Invalid amount"
