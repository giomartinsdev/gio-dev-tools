Feature: Move / rename resource

  Scenario: Rename a file
    Given the WebDAV move succeeds
    When I send PATCH with from "gio/old.md" and to "gio/new.md"
    Then the response status is 200
    And the response body has field "moved" equal to "True"
    And move_resource was called with from "gio/old.md" and to "gio/new.md"

  Scenario: Missing from path returns 400
    When I send PATCH with from "" and to "gio/new.md"
    Then the response status is 400

  Scenario: Missing to path returns 400
    When I send PATCH with from "gio/old.md" and to ""
    Then the response status is 400

  Scenario: WebDAV move failure returns 400
    Given the WebDAV move raises an error
    When I send PATCH with from "gio/old.md" and to "gio/new.md"
    Then the response status is 400
