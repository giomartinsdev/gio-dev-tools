Feature: RabbitMQ publisher
  As the bus-tracker-poller worker
  I want domain events published with the right routing key
  So that bus-tracker's consumer actually catches them

  Background:
    Given a connected fake RabbitMQ publisher

  Scenario: Publishing a domain event routes on its event_type
    When I publish a BusPositionCaptured domain event
    Then the domain exchange received a message with routing key "bus.position_captured"

  Scenario: Closing the publisher closes the underlying connection
    When I close the publisher
    Then the underlying connection was closed
