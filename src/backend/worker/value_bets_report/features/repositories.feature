Feature: Config and recipients repositories
  As the value_bets_report worker
  I want config and recipients persisted through TransactionManager sessions
  So that the FastAPI routes and scheduler read/write real state

  Scenario: ConfigRepository.get reads the singleton row
    Given a fake transaction manager returning a config row
    When I get the config
    Then the config has send_time "00:00"

  Scenario: ConfigRepository.update writes the singleton row
    Given a fake transaction manager returning a config row
    When I update the config to send_time "08:00", offset 0, enabled false
    Then the row was updated with send_time "08:00"

  Scenario: RecipientsRepository.create adds a recipient
    Given a fake transaction manager for recipients
    When I create a recipient with phone "5511999999999" and name "Gio"
    Then a recipient row was added

  Scenario: RecipientsRepository.list_active filters inactive rows
    Given a fake transaction manager listing 1 active and 1 inactive recipient
    When I list active recipients
    Then 1 active recipient is returned

  Scenario: RecipientsRepository.list_all returns every recipient
    Given a fake transaction manager listing 1 active and 1 inactive recipient
    When I list all recipients
    Then 2 recipients are returned

  Scenario: RecipientsRepository.delete removes a recipient
    Given a fake transaction manager for recipients
    When I delete recipient 1
    Then a delete was issued for recipient 1

  Scenario: RecipientsRepository.set_active returns None when missing
    Given a fake transaction manager with no matching recipient row
    When I set active for recipient 99
    Then the result is empty

  Scenario: RecipientsRepository.set_realtime_alerts toggles the flag
    Given a fake transaction manager for recipients
    When I set realtime alerts for recipient 1 to true
    Then the returned recipient has realtime alerts enabled

  Scenario: RealtimeAlertLogRepository.is_alerted reports false when absent
    Given a fake transaction manager with no alert log row
    When I check if the value bet was alerted
    Then it reports not alerted

  Scenario: RealtimeAlertLogRepository.is_alerted reports true when present
    Given a fake transaction manager with an existing alert log row
    When I check if the value bet was alerted
    Then it reports alerted

  Scenario: RealtimeAlertLogRepository.mark_alerted inserts a row
    Given a fake transaction manager for the alert log
    When I mark the value bet as alerted
    Then an alert log insert was executed
