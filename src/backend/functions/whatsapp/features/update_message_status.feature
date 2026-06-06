Feature: Update message status from Evolution API

  Scenario: READ status is mapped and persisted
    Given an empty store
    And message "m1" exists with status "pending"
    When I update message "m1" status to "READ"
    Then message "m1" has status "read"

  Scenario: DELIVERY_ACK is mapped to delivered
    Given an empty store
    And message "m1" exists with status "pending"
    When I update message "m1" status to "DELIVERY_ACK"
    Then message "m1" has status "delivered"

  Scenario: MessageStatusUpdated event is published
    Given an empty store
    And message "m1" exists with status "pending"
    When I update message "m1" status to "READ"
    Then a MessageStatusUpdated event was published with message_id "m1" and status "read"
