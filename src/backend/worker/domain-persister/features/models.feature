Feature: Schema-aware table creation
  As the domain-persister
  I want create_all() to create the bzzoiro_data schema before the tables
  So that Postgres (which never auto-creates schemas) has somewhere to put them

  Scenario: create_all creates the schema then the tables
    Given a mocked engine
    When create_all runs against it
    Then the schema was created before the tables
