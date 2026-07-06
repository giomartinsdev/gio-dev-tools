Feature: WhatsApp value-bet notifier
  As the domain-persister
  I want to publish an alert to the same queue whatsapp-worker consumes
  So that a new value bet reaches a real phone without a dashboard

  Background:
    Given a fresh whatsapp notifier

  Scenario: notify publishes to the whatsapp-send queue with the configured number
    When I send a notification with text "hello"
    Then a message was published to the whatsapp-send queue with number and text "hello"

  Scenario: notify includes the instance when one is configured
    Given the notifier has an instance configured
    When I send a notification with text "hello"
    Then the published message includes the configured instance
