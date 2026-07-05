Feature: Read-side query handlers
  As a caller of domain-persister's HTTP API
  I want list/get queries to just delegate to the repository
  So that matches can be looked up by id or listed with pagination

  Background:
    Given a fake read model repository

  Scenario: ListMatchesHandler delegates to find_all_matches with the given paging
    When I list matches with limit 10 and offset 5
    Then find_all_matches was called with limit 10 and offset 5

  Scenario: GetMatchHandler delegates to find_match
    When I get match "abc-123"
    Then find_match was called with "abc-123"
