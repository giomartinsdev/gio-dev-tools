Feature: Financial summary
  As a user
  I want to see a summary of my income and expenses
  So that I can understand my net financial position

  Background:
    Given an empty transaction repository

  Scenario: Empty repository returns all-zero summary
    When I request the summary
    Then the total income is "0"
    And the total expenses are "0"
    And the balance is "0"
    And the transaction count is 0

  Scenario: Summary with only income
    Given I have recorded an income of "1000.00" in category "Salary" described as "Job"
    And I have recorded an income of "500.00" in category "Freelance" described as "Project"
    When I request the summary
    Then the total income is "1500.00"
    And the total expenses are "0"
    And the balance is "1500.00"
    And the transaction count is 2

  Scenario: Summary with only expenses produces negative balance
    Given I have recorded an expense of "200.00" in category "Rent" described as "Apartment"
    When I request the summary
    Then the total income is "0"
    And the total expenses are "200.00"
    And the balance is "-200.00"
    And the transaction count is 1

  Scenario: Summary with mixed transactions
    Given I have recorded an income of "3000.00" in category "Salary" described as "Job"
    And I have recorded an expense of "1200.00" in category "Rent" described as "Apartment"
    And I have recorded an expense of "400.00" in category "Food" described as "Groceries"
    When I request the summary
    Then the total income is "3000.00"
    And the total expenses are "1600.00"
    And the balance is "1400.00"
    And the transaction count is 3

  Scenario: Summary filtered by month excludes other months
    Given I have recorded on "2025-01-15" an income of "1000.00" in category "Salary" described as "January"
    And I have recorded on "2025-02-15" an income of "1000.00" in category "Salary" described as "February"
    When I request the summary for month 1 of year 2025
    Then the total income is "1000.00"
    And the transaction count is 1

  Scenario: Summary filtered by year excludes other years
    Given I have recorded on "2024-06-01" an income of "5000.00" in category "Salary" described as "2024 income"
    And I have recorded on "2025-06-01" an income of "6000.00" in category "Salary" described as "2025 income"
    When I request the summary for month 6 of year 2025
    Then the total income is "6000.00"
    And the transaction count is 1
