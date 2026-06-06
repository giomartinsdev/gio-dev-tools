Feature: Record a financial transaction
  As a user tracking my finances
  I want to record income and expense transactions
  So that I can monitor my financial activity

  Background:
    Given an empty transaction repository

  Scenario: Record a valid income transaction
    When I record an income of "100.00" in category "Salary" described as "Monthly salary"
    Then 1 transaction is saved
    And the transaction type is "income"
    And the transaction amount is "100.00"
    And a TransactionRecorded event is published

  Scenario: Record a valid expense transaction
    When I record an expense of "45.50" in category "Food" described as "Lunch at restaurant"
    Then 1 transaction is saved
    And the transaction type is "expense"
    And the transaction amount is "45.50"
    And a TransactionRecorded event is published

  Scenario Outline: Reject zero amounts
    When I try to record an income of "<amount>" in category "Test" described as "Test"
    Then a validation error contains "cannot be zero"

    Examples:
      | amount |
      | 0      |
      | 0.00   |
      | 0.0    |

  Scenario Outline: Reject non-numeric amounts
    When I try to record an income of "<amount>" in category "Test" described as "Test"
    Then a validation error contains "Invalid amount"

    Examples:
      | amount  |
      | abc     |
      | 1.2.3   |
      | --10    |

  Scenario: Reject blank or whitespace-only category
    When I try to record an income of "100.00" in category "   " described as "Test"
    Then a validation error contains "category is required"

  Scenario: Reject blank or whitespace-only description
    When I try to record an income of "100.00" in category "Test" described as "   "
    Then a validation error contains "description is required"

  Scenario Outline: Reject invalid transaction types
    When I try to record a "<type>" of "100.00" in category "Test" described as "Test"
    Then a validation error contains "Invalid type"

    Examples:
      | type      |
      | transfer  |
      | debit     |
      | INCOME    |
      | EXPENSE   |
