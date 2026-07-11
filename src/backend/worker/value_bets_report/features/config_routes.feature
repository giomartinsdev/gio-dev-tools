Feature: Config routes
  As the dev-tools dashboard
  I want to read and update the report schedule
  So that the send time, reference day, and enabled flag are editable from the UI

  Scenario: GET /config returns the persisted row
    Given a config repository returning send_time "00:00", offset 1, enabled
    When I call the get_config endpoint
    Then the returned config has send_time "00:00"

  Scenario: PUT /config persists changes
    Given a config repository
    When I call the put_config endpoint with send_time "08:30", offset 0, enabled false
    Then the config repository was updated with send_time "08:30", offset 0, enabled false
