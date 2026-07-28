Feature: Publish outbound WhatsApp replies to the send queue

  Scenario: A reply is published to the whatsapp-send queue
    Given a fake RabbitMQ connection
    When I send a WhatsApp reply to "5511999@s.whatsapp.net" with text "oi"
    Then a message was published to queue "whatsapp-send" with number "5511999@s.whatsapp.net" and text "oi"
