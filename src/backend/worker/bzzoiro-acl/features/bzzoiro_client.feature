Feature: bzzoiro REST client
  As the bzzoiro anti-corruption layer
  I want pagination, rate-limit backoff and error handling to work correctly
  So that a slow/rate-limiting/flaky upstream doesn't break polling

  Scenario: fetch_events paginates v2 events via envelope shape
    Given a bzzoiro v2 API that returns 2 pages of events as envelope
    When I fetch events from the client
    Then all results across both pages are returned

  Scenario: fetch_events accepts a flat array response from v2
    Given a bzzoiro v2 API that returns 1 flat page of events
    When I fetch events from the client
    Then the flat event page is returned

  Scenario Outline: fetch_events translates our status vocabulary to bzzoiro's real v2 enum
    Given a bzzoiro v2 API recording requests and returning 1 page of events
    When I fetch events with status "<our_status>" from the client
    Then the request was sent with status "<bzzoiro_status>"

    Examples:
      | our_status | bzzoiro_status |
      | upcoming   | notstarted     |
      | live       | inprogress     |
      | finished   | finished       |
      | halftime   | halftime       |

  Scenario: A 429 is retried and eventually succeeds
    Given a bzzoiro API that returns 429 once then succeeds
    When I fetch events from the client
    Then the results from the successful response are returned

  Scenario: A 401 raises an auth error
    Given a bzzoiro API that returns 401
    When I fetch events from the client
    Then a BzzoiroAuthError is raised

  Scenario: A 404 is treated as an empty page
    Given a bzzoiro API that returns 404
    When I fetch events from the client
    Then an empty list is returned

  Scenario: fetch_live returns events from the v2 live endpoint (envelope shape)
    Given a bzzoiro v2 API that returns 1 page of live events as envelope
    When I fetch live events from the client
    Then all results from the live page are returned

  Scenario: fetch_live accepts a flat array from the v2 live endpoint
    Given a bzzoiro v2 API that returns 1 flat page of live events
    When I fetch live events from the client
    Then the flat live page is returned

  Scenario: fetch_odds paginates a v2 flat array across two full pages
    Given a bzzoiro v2 API that returns 2 full pages of odds
    When I fetch odds from the client
    Then all odds rows across both pages are returned

  Scenario: fetch_odds stops after a partial page
    Given a bzzoiro v2 API that returns 1 partial page of odds
    When I fetch odds from the client
    Then only the partial page of odds is returned

  Scenario: fetch_odds treats a 404 as an empty list
    Given a bzzoiro API that returns 404
    When I fetch odds from the client
    Then an empty list is returned

  Scenario: fetch_predictions paginates a v2 flat array
    Given a bzzoiro v2 API that returns 1 page of predictions
    When I fetch predictions from the client
    Then all prediction rows are returned

  Scenario: fetch_odds paginates the real {count,next,results} envelope
    Given a bzzoiro v2 API that returns 2 enveloped pages of odds
    When I fetch odds from the client
    Then all odds rows across both pages are returned

  Scenario: fetch_predictions also accepts the enveloped shape
    Given a bzzoiro v2 API that returns 1 enveloped page of predictions
    When I fetch predictions from the client
    Then all prediction rows are returned

  # ── New: teams client scenarios ──────────────────────────────────────────────
  
  Scenario: fetch_teams paginates a v2 flat array
    Given a bzzoiro v2 API that returns 1 page of teams
    When I fetch teams from the client
    Then all team rows are returned

  Scenario: fetch_squad returns the team squad list
    Given a bzzoiro v2 API that returns a squad for team 444
    When I fetch squad for team 444 from the client
    Then the squad list is returned


  # ── New: transient error handling (ReadTimeout / 502) ────────────────────────

  Scenario: A 502 is retried and eventually succeeds (positive)
    Given a bzzoiro API that returns 502 once then succeeds with one odds row
    When I fetch odds from the client
    Then only one odds row is returned without error

  Scenario: Repeated ReadTimeouts exhaust retries and raise an error (negative)
    Given a bzzoiro API that always raises ReadTimeout
    When I fetch odds from the client
    Then a BzzoiroTransientError is raised

  # ── New: odds comparison / polymarket client scenarios ───────────────────────

  Scenario: fetch_odds_comparison returns the comparison payload
    Given a bzzoiro API that returns an odds comparison payload for event 900
    When I fetch odds comparison for event 900 from the client
    Then the odds comparison payload is returned

  Scenario: fetch_odds_comparison returns None when bzzoiro has no odds for the event
    Given a bzzoiro API that returns 404
    When I fetch odds comparison for event 900 from the client
    Then None is returned by the client

  Scenario: fetch_polymarket returns None when no markets are available
    Given a bzzoiro API that returns 404
    When I fetch polymarket for event 900 from the client
    Then None is returned by the client

  # ── New: lineups / h2h / odds-best / standings client scenarios ──────────────

  Scenario: fetch_lineups returns the predicted lineup payload
    Given a bzzoiro API that returns a lineups payload for event 900
    When I fetch lineups for event 900 from the client
    Then the lineups payload is returned

  Scenario: fetch_lineups returns None when no lineup prediction exists yet
    Given a bzzoiro API that returns 404
    When I fetch lineups for event 900 from the client
    Then None is returned by the client

  Scenario: fetch_h2h returns the head-to-head payload
    Given a bzzoiro API that returns a h2h payload for event 900
    When I fetch h2h for event 900 from the client
    Then the h2h payload is returned

  Scenario: fetch_odds_best returns the best-odds rows
    Given a bzzoiro v2 API that returns 1 page of best odds
    When I fetch odds best from the client
    Then the odds best rows are returned

  Scenario: fetch_standings returns the league table payload
    Given a bzzoiro API that returns a standings payload for league 40
    When I fetch standings for league 40 from the client
    Then the standings payload is returned

  Scenario: fetch_standings returns None when the league has no standings
    Given a bzzoiro API that returns 404
    When I fetch standings for league 40 from the client
    Then None is returned by the client

  # ── New: venues / referees / player-stats / incidents client scenarios ────────

  Scenario: fetch_venue returns the venue payload
    Given a bzzoiro API that returns a venue payload for venue 735
    When I fetch venue 735 from the client
    Then the venue payload is returned

  Scenario: fetch_venue returns None when the venue does not exist
    Given a bzzoiro API that returns 404
    When I fetch venue 735 from the client
    Then None is returned by the client

  Scenario: fetch_referee returns the referee payload
    Given a bzzoiro API that returns a referee payload for referee 2535
    When I fetch referee 2535 from the client
    Then the referee payload is returned

  Scenario: fetch_referee returns None when the referee does not exist
    Given a bzzoiro API that returns 404
    When I fetch referee 2535 from the client
    Then None is returned by the client

  Scenario: fetch_player_stats returns the player stats payload
    Given a bzzoiro API that returns a player stats payload for event 8378
    When I fetch player stats for event 8378 from the client
    Then the player stats payload is returned

  Scenario: fetch_player_stats returns None before kickoff
    Given a bzzoiro API that returns 404
    When I fetch player stats for event 8378 from the client
    Then None is returned by the client

  Scenario: fetch_incidents returns the incidents payload
    Given a bzzoiro API that returns an incidents payload for event 8378
    When I fetch incidents for event 8378 from the client
    Then the incidents payload is returned

  Scenario: fetch_incidents returns None before kickoff
    Given a bzzoiro API that returns 404
    When I fetch incidents for event 8378 from the client
    Then None is returned by the client
