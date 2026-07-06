Feature: Sync checkpoint repository
  As the bzzoiro anti-corruption layer
  I want to remember how far each poll loop has gotten
  So that a restart resumes instead of re-fetching everything from scratch

  Background:
    Given a fresh sync checkpoint table

  Scenario: A feed type with no checkpoint returns None
    When I get the cursor for "odds"
    Then the cursor is None

  Scenario: Setting a cursor persists it
    When I set the cursor for "odds" to "2026-08-01T09:00:00+00:00"
    And I get the cursor for "odds"
    Then the cursor is "2026-08-01T09:00:00+00:00"

  Scenario: Setting a cursor again overwrites the previous value
    Given the cursor for "odds" is "2026-08-01T09:00:00+00:00"
    When I set the cursor for "odds" to "2026-08-01T10:00:00+00:00"
    And I get the cursor for "odds"
    Then the cursor is "2026-08-01T10:00:00+00:00"

  Scenario: Different feed types have independent cursors
    Given the cursor for "odds" is "2026-08-01T09:00:00+00:00"
    When I set the cursor for "teams" to "2026-08-01T00:00:00+00:00"
    And I get the cursor for "odds"
    Then the cursor is "2026-08-01T09:00:00+00:00"

  Scenario: Clearing a feed type removes its checkpoint
    Given the cursor for "odds" is "2026-08-01T09:00:00+00:00"
    When I clear the checkpoint for "odds"
    And I get the cursor for "odds"
    Then the cursor is None

  Scenario: Clearing all feed types removes every checkpoint
    Given the cursor for "odds" is "2026-08-01T09:00:00+00:00"
    And the cursor for "teams" is "2026-08-01T00:00:00+00:00"
    When I clear all checkpoints
    And I get the cursor for "odds"
    Then the cursor is None
