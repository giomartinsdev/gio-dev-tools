Feature: Extract amount from OCR text

  Scenario: Extract amount after TOTAL label
    When I extract the amount from "TOTAL R$ 45.90"
    Then the amount is "45.90"

  Scenario: Extract amount after VALOR TOTAL label
    When I extract the amount from "VALOR TOTAL: 120,50"
    Then the amount is "120.50"

  Scenario: Extract R$ formatted amount
    When I extract the amount from "R$ 9,99"
    Then the amount is "9.99"

  Scenario: Extract Brazilian thousand-separated format
    When I extract the amount from "TOTAL 1.250,00"
    Then the amount is "1250.00"

  Scenario: Return None when no amount found
    When I extract the amount from "sem valor aqui"
    Then no amount is extracted
