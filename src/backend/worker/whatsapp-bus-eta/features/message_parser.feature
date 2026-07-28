Feature: Parse an Evolution API messages.upsert payload

  Scenario: A plain text message is parsed
    Given an Evolution payload with jid "5511999@s.whatsapp.net" and text "483"
    When I parse the Evolution payload
    Then the parsed remote jid is "5511999@s.whatsapp.net"
    And the parsed text is "483"
    And no location was parsed

  Scenario: A location message is parsed
    Given an Evolution payload with jid "5511999@s.whatsapp.net" and location -22.9068 -43.1729
    When I parse the Evolution payload
    Then the parsed latitude is -22.9068 and longitude is -43.1729

  Scenario: A message sent by us is flagged as from_me
    Given an Evolution payload with jid "5511999@s.whatsapp.net" and text "oi" from me
    When I parse the Evolution payload
    Then the parsed message is from me
