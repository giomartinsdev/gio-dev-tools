Feature: Parse a WhatsApp text message into a line query

  Scenario: A bare line code defaults to SPPO
    When I parse the text "483"
    Then the parsed mode is "sppo" and line code "483"

  Scenario: A mode-prefixed line code is respected
    When I parse the text "brt 22"
    Then the parsed mode is "brt" and line code "22"

  Scenario Outline: Uppercase mode prefix is accepted case-insensitively
    When I parse the text "<text>"
    Then the parsed mode is "<mode>" and line code "<line_code>"

    Examples:
      | text      | mode | line_code |
      | SPPO 840  | sppo | 840       |
      | Brt 40    | brt  | 40        |

  Scenario: A regular chat sentence does not parse as a line query
    When I parse the text "oi tudo bem?"
    Then no line query is parsed

  Scenario: Empty text does not parse as a line query
    When I parse the text ""
    Then no line query is parsed
