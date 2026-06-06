Feature: Extract date from OCR text

  Scenario: Extract date in DD/MM/YYYY format
    When I extract the date from "Data: 15/03/2024"
    Then the date is "2024-03-15"

  Scenario: Extract date in YYYY-MM-DD format
    When I extract the date from "date 2024-06-01 total"
    Then the date is "2024-06-01"

  Scenario: Return None when no date found
    When I extract the date from "sem data aqui"
    Then no date is extracted
