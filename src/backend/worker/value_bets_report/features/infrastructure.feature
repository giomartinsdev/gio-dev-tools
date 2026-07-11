Feature: Infrastructure publishers
  As the value_bets_report worker
  I want the WhatsApp publisher and trigger queue to talk to RabbitMQ correctly
  So that reports and triggers actually reach their queues

  Scenario: WhatsAppPublisher publishes to the whatsapp-send queue
    Given a fresh whatsapp publisher
    When I publish "hello" to "5511999999999"
    Then a message was published to the whatsapp-send queue with number "5511999999999" and text "hello"

  Scenario: WhatsAppPublisher includes the instance when one is given
    Given a fresh whatsapp publisher
    When I publish "hello" to "5511999999999" with instance "admin"
    Then the published whatsapp message includes the instance "admin"

  Scenario: TriggerPublisher publishes a trigger message
    Given a fresh trigger publisher
    When I publish a trigger with reason "manual"
    Then a message was published to the value-bets-report-trigger queue with reason "manual"

  Scenario: value bets client paginates until a short page
    Given a value bets client returning a full page then a short page
    When I fetch value bets
    Then all pages were combined into the result

  Scenario: value bets outcomes client stops paginating once it passes the cutoff day
    Given an outcomes client returning pages older than the cutoff after the first page
    When I fetch outcomes with cutoff "2026-07-11"
    Then only the first page of outcomes is in the result

  Scenario: consume_triggers acks a good message and nacks a poison one
    Given a fake broker with one good trigger message and one poison trigger message
    When the trigger consumer runs one connection cycle
    Then the on_trigger callback ran once and the good message was acked
    And the poison message was nacked without requeue

