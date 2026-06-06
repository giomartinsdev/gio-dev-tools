Feature: Write file

  Scenario: Create a new file
    Given the WebDAV write succeeds
    When I send POST with path "gio/new.md" and content "hello"
    Then the response status is 201
    And the response body has field "created" equal to "True"
    And write_file was called with path "gio/new.md" and content "hello"

  Scenario: Create file without path returns 400
    When I send POST with no path and content "hello"
    Then the response status is 400

  Scenario: Update an existing file
    Given the WebDAV write succeeds
    When I send PUT with path "gio/existing.md" and content "updated"
    Then the response status is 200
    And the response body has field "updated" equal to "True"
    And write_file was called with path "gio/existing.md" and content "updated"

  Scenario: Update file without path returns 400
    When I send PUT with no path and content "x"
    Then the response status is 400

  Scenario: Create a directory
    Given the WebDAV mkdir succeeds
    When I send POST mkdir with path "gio/NewFolder"
    Then the response status is 201
    And the response body has field "created" equal to "True"
    And make_directory was called with path "gio/NewFolder"
