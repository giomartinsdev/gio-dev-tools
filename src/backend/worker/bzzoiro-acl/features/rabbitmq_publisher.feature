Feature: RabbitMQ publisher
  As the bzzoiro anti-corruption layer
  I want raw and domain events published with the right routing keys
  So that domain-persister's bindings actually catch them

  Background:
    Given a connected fake RabbitMQ publisher

  Scenario: Publishing a raw feed uses the raw.bzzoiro.{feed_type} routing key
    When I publish a raw "fixtures" feed
    Then the ingestion exchange received a message with routing key "raw.bzzoiro.fixtures"

  Scenario: Publishing a domain event routes on its event_type
    When I publish a MatchStatusChanged domain event
    Then the domain exchange received a message with routing key "match.status_changed"

  Scenario: Closing the publisher closes the underlying connection
    When I close the publisher
    Then the underlying connection was closed
