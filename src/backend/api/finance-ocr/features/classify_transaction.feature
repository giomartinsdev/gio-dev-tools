Feature: Classify transaction from OCR text

  Scenario: Income keywords produce income type
    When I classify the text "salário recebido em conta corrente"
    Then the type is "income" and category is "Transaction"

  Scenario: PIX keyword produces Transaction expense
    When I classify the text "pagamento via pix efetuado"
    Then the type is "expense" and category is "Transaction"

  Scenario: Food keyword produces Food expense
    When I classify the text "restaurante japonês - 2 pessoas"
    Then the type is "expense" and category is "Food"

  Scenario: Health keyword produces Health expense
    When I classify the text "compra na farmácia drogaria raia"
    Then the type is "expense" and category is "Health"

  Scenario: Entertainment keyword produces Entertainment expense
    When I classify the text "assinatura netflix mensal"
    Then the type is "expense" and category is "Entertainment"

  Scenario: Education keyword produces Education expense
    When I classify the text "mensalidade faculdade particular"
    Then the type is "expense" and category is "Education"

  Scenario: Shopping keyword produces Shopping expense
    When I classify the text "compra magazine luiza geladeira"
    Then the type is "expense" and category is "Shopping"

  Scenario: Unknown text defaults to Other expense
    When I classify the text "xyzabc 12345"
    Then the type is "expense" and category is "Other"
