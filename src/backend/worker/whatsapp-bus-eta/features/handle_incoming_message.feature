Feature: Reply with a bus ETA once both location and line are known

  Scenario: Location arrives first, then the line — full ETA with a stop
    Given no conversation state exists
    And the bus tracker has a live bus for mode "sppo" line "483" at -22.90 -43.20 speed 20
    And the bus tracker has a stop for mode "sppo" line "483" named "Praça Central" at -22.901 -43.201
    And OSRM reports a walk of 4 minutes and a drive of 6 minutes
    When the user shares their location -22.9 -43.2
    Then no reply is sent yet
    When the user sends the text "483"
    Then a reply is sent containing "Praça Central"
    And a reply is sent containing "4 min"
    And a reply is sent containing "6 min"

  Scenario: Line arrives first, then the location
    Given no conversation state exists
    And the bus tracker has a live bus for mode "brt" line "22" at -22.90 -43.20 speed 25
    And no stops are registered for mode "brt" line "22"
    When the user sends the text "brt 22"
    Then no reply is sent yet
    When the user shares their location -22.9 -43.2
    Then a reply is sent containing "linha reta"

  Scenario: No live buses yet on the requested line
    Given no conversation state exists
    And the bus tracker has no live buses for mode "sppo" line "999"
    When the user sends the text "999"
    And the user shares their location -22.9 -43.2
    Then a reply is sent containing "ainda não tenho ônibus"

  Scenario: A message sent by us is ignored
    Given no conversation state exists
    When a message from me with text "483" arrives
    Then no reply is sent yet
