Feature: Recipients routes
  As the dev-tools dashboard
  I want to manage who receives the report
  So that recipients can be added, listed, toggled, and removed from the UI

  Scenario: POST /recipients creates a recipient
    Given a recipients repository
    When I call the create_recipient endpoint with phone "5511999999999" and name "Gio"
    Then the repository created a recipient with phone "5511999999999" and name "Gio"

  Scenario: GET /recipients lists all recipients
    Given a recipients repository returning 2 recipients
    When I call the list_recipients endpoint
    Then 2 recipients are returned

  Scenario: PATCH /recipients/{id} toggles active
    Given a recipients repository that can toggle recipient 1
    When I call the update_recipient endpoint for id 1 with active false
    Then the returned recipient is inactive

  Scenario: PATCH /recipients/{id} toggles realtime alerts
    Given a recipients repository that can toggle realtime alerts for recipient 1
    When I call the update_recipient endpoint for id 1 with realtime_alerts true
    Then the returned recipient has realtime alerts enabled

  Scenario: PATCH /recipients/{id} 404s when not found
    Given a recipients repository with no matching recipient
    When I call the update_recipient endpoint for id 99 with active false expecting an error
    Then a 404 HTTPException is raised

  Scenario: DELETE /recipients/{id} removes it
    Given a recipients repository
    When I call the delete_recipient endpoint for id 1
    Then the repository deleted recipient 1
