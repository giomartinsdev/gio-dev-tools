Feature: Read file

  Scenario: Read an existing file returns its content
    Given the WebDAV file "gio/Notes/hello.md" has content "# Hello"
    When I send GET with path "gio/Notes/hello.md" and type "file"
    Then the response status is 200
    And the response body has field "content" equal to "# Hello"
    And the response body has field "path" equal to "gio/Notes/hello.md"

  Scenario: Reading a non-existent file returns 400
    Given the WebDAV file read raises an error
    When I send GET with path "gio/missing.md" and type "file"
    Then the response status is 400
