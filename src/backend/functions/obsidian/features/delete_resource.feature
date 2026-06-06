Feature: Delete resource

  Scenario: Delete a file
    Given the WebDAV delete succeeds
    When I send DELETE with path "gio/old.md"
    Then the response status is 200
    And the response body has field "deleted" equal to "True"
    And delete_resource was called with path "gio/old.md"

  Scenario: Delete without path returns 400
    When I send DELETE with no path
    Then the response status is 400

  Scenario: WebDAV delete failure returns 400
    Given the WebDAV delete raises an error
    When I send DELETE with path "gio/old.md"
    Then the response status is 400
