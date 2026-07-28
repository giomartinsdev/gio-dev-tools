Feature: Persist per-chat conversation state

  Scenario: An unknown chat has no location or line yet
    Given no row exists for jid "5511999@s.whatsapp.net"
    When I get the state for jid "5511999@s.whatsapp.net"
    Then the state has no location and no line

  Scenario: A known chat's location and line are returned
    Given a row exists for jid "5511999@s.whatsapp.net" with lat -22.9 lon -43.2 mode "sppo" line "483"
    When I get the state for jid "5511999@s.whatsapp.net"
    Then the state has location -22.9 -43.2 and line "sppo" "483"

  Scenario: Setting a location upserts the row
    When I set the location for jid "5511999@s.whatsapp.net" to -22.9 -43.2
    Then an upsert was executed

  Scenario: Setting a line upserts the row
    When I set the line for jid "5511999@s.whatsapp.net" to mode "brt" line "22"
    Then an upsert was executed
