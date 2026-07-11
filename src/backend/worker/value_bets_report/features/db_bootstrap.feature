Feature: Database bootstrap
  As the value_bets_report worker
  I want my dedicated database created if it doesn't exist yet
  So that SQLAlchemy's create_all has somewhere to create tables

  Scenario: creates the database when it doesn't exist
    Given an admin connection reporting the database is missing
    When I ensure the database exists
    Then a CREATE DATABASE statement was executed

  Scenario: does nothing when the database already exists
    Given an admin connection reporting the database already exists
    When I ensure the database exists
    Then no CREATE DATABASE statement was executed
