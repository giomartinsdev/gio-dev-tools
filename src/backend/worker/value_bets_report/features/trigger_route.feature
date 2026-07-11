Feature: Manual trigger route
  As the dev-tools dashboard
  I want an "Enviar agora" button to send the report immediately
  So that the schedule doesn't have to be waited on to test or force a resend

  Scenario: POST /trigger publishes to the trigger queue immediately
    Given a trigger publisher
    When I call the trigger_now endpoint
    Then the trigger publisher published with reason "manual"
