Feature: List directory

  Scenario: List a directory returns sorted entries
    Given the WebDAV directory "gio" contains a folder "Notes" and a file "readme.md"
    When I send GET with path "gio" and type "dir"
    Then the response status is 200
    And the response contains 2 entries
    And the first entry is a directory named "Notes"
    And the second entry is a file named "readme.md"

  Scenario: Default path is "gio"
    Given the WebDAV directory "gio" contains a file "index.md"
    When I send GET with no path
    Then the response status is 200
    And the response contains 1 entries

  Scenario: WebDAV error propagates as 400
    Given the WebDAV directory listing raises an error
    When I send GET with path "gio" and type "dir"
    Then the response status is 400
