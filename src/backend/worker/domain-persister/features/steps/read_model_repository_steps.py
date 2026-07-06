from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from behave import given, then, use_step_matcher, when

from src.infrastructure.read_model_repository import ReadModelRepository

use_step_matcher("re")


class _FakeTransactionManager:
    def __init__(self, session):
        self._session = session

    @contextmanager
    def session(self):
        yield self._session

    @contextmanager
    def read_only(self):
        yield self._session


@given('a fake transaction manager for the read model repository')
def step_fake_tm(context):
    context.session = Mock()
    context.repo = ReadModelRepository()
    context.result = None
    fake_tm = _FakeTransactionManager(context.session)
    tm_patch = patch(
        "src.infrastructure.read_model_repository.TransactionManager.get", return_value=fake_tm,
    )
    tm_patch.start()
    context.add_cleanup(tm_patch.stop)


@when('I upsert a scheduled match')
def step_upsert_scheduled(context):
    context.repo.upsert_match_scheduled(
        match_id=uuid4(), competition_id=uuid4(), home_team_id=uuid4(), away_team_id=uuid4(),
        kickoff_at=datetime.now(timezone.utc), venue="Emirates",
    )


@when('I upsert a match status')
def step_upsert_status(context):
    context.repo.upsert_match_status(match_id=uuid4(), status="LIVE", minute=12)


@when('I upsert a match score')
def step_upsert_score(context):
    context.repo.upsert_match_score(match_id=uuid4(), home_score=1, away_score=0, minute=30)


@when('I upsert a finished match')
def step_upsert_finished(context):
    context.repo.upsert_match_finished(match_id=uuid4(), home_score=2, away_score=1, statistics={"shots": 10})


@when('I insert an odds snapshot')
def step_insert_odds(context):
    context.repo.insert_odds_snapshot(
        event_id=uuid4(), match_id=uuid4(), bookmaker="aggregate", market="1x2",
        selections=[{"name": "home", "price": "2.10"}], captured_at=datetime.now(timezone.utc),
    )


@when('I upsert an odds comparison')
def step_upsert_odds_comparison(context):
    context.repo.upsert_odds_comparison(
        match_id=uuid4(), bookmakers_count=3, total_odds=10,
        markets={"1x2": {"HOME": {"best_odds": 2.1}}}, captured_at=datetime.now(timezone.utc),
    )


@when('I upsert a polymarket snapshot')
def step_upsert_polymarket(context):
    context.repo.upsert_polymarket_snapshot(
        match_id=uuid4(), markets={"1x2": {"HOME": 0.5}}, captured_at=datetime.now(timezone.utc),
    )


@when('I upsert a value bet')
def step_upsert_value_bet(context):
    context.repo.upsert_value_bet(
        match_id=uuid4(), market="1x2", outcome="HOME", model_probability="0.60",
        bookmaker="bet365", best_odds="2.20", implied_probability="0.4545", edge="0.1455",
        detected_at=datetime.now(timezone.utc),
    )


@when('I delete a value bet')
def step_delete_value_bet(context):
    context.repo.delete_value_bet(match_id=uuid4(), market="1x2", outcome="HOME")


@then('a delete was issued against the value_bets table')
def step_assert_delete_issued(context):
    context.session.query.return_value.filter.return_value.delete.assert_called_once()


@when('I merge odds comparison markets')
def step_merge_odds_comparison_markets(context):
    context.repo.merge_odds_comparison_markets(
        match_id=uuid4(), markets_patch={"1x2": {"HOME": {"best_odds": 2.3}}},
        captured_at=datetime.now(timezone.utc),
    )


@when('I upsert lineups')
def step_upsert_lineups(context):
    context.repo.upsert_lineups(
        match_id=uuid4(), lineup_status="predicted",
        lineups={"home": {"confidence": 0.8}, "away": {"confidence": 0.7}},
        captured_at=datetime.now(timezone.utc),
    )


@when('I upsert h2h')
def step_upsert_h2h(context):
    context.repo.upsert_h2h(match_id=uuid4(), h2h={"total_matches": 0}, captured_at=datetime.now(timezone.utc))


@when('I upsert standings')
def step_upsert_standings(context):
    context.repo.upsert_standings(
        competition_id=uuid4(), standings={"standings": []}, captured_at=datetime.now(timezone.utc),
    )


@when('I insert an insight')
def step_insert_insight(context):
    context.repo.insert_insight(
        insight_id=uuid4(), match_id=uuid4(), market="match_result", recommendation="favorite:H",
        confidence="0.82", rationale="test", model="v4", feature_snapshot={},
        generated_at=datetime.now(timezone.utc),
    )


@then(r'the session executed a statement against "([^"]+)"')
def step_assert_table(context, table_name):
    context.session.execute.assert_called_once()
    stmt = context.session.execute.call_args[0][0]
    assert stmt.table.name == table_name, f"expected {table_name}, got {stmt.table.name}"


def _fake_match_row():
    return SimpleNamespace(
        match_id=str(uuid4()), competition_id=str(uuid4()), home_team_id=str(uuid4()),
        away_team_id=str(uuid4()), status="LIVE", home_score=1, away_score=0, minute=10,
        kickoff_at=datetime.now(timezone.utc), venue="Emirates", statistics=None,
    )


@given('the session query returns 1 match row')
def step_query_returns_row(context):
    row = _fake_match_row()
    context.session.query.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = [row]


@given('the session get returns a match row')
def step_get_returns_row(context):
    context.session.get.return_value = _fake_match_row()


@given('the session get returns no row')
def step_get_returns_none(context):
    context.session.get.return_value = None


def _fake_odds_comparison_row():
    return SimpleNamespace(
        match_id=str(uuid4()), bookmakers_count=3, total_odds=10,
        markets={"1x2": {"HOME": {"best_odds": 2.1}}}, captured_at=datetime.now(timezone.utc),
    )


@given('the session get returns an odds comparison row')
def step_get_returns_odds_comparison_row(context):
    context.session.get.return_value = _fake_odds_comparison_row()


@when('I get the odds comparison')
def step_get_odds_comparison(context):
    context.result = context.repo.find_odds_comparison("some-id")


@then('an odds comparison dict is returned')
def step_assert_odds_comparison_dict(context):
    assert context.result is not None
    assert "markets" in context.result


def _fake_lineups_row():
    return SimpleNamespace(
        match_id=str(uuid4()), lineup_status="predicted",
        lineups={"home": {"confidence": 0.8}, "away": {"confidence": 0.7}},
        captured_at=datetime.now(timezone.utc),
    )


@given('the session get returns a lineups row')
def step_get_returns_lineups_row(context):
    context.session.get.return_value = _fake_lineups_row()


@when('I get the lineups')
def step_get_lineups(context):
    context.result = context.repo.find_lineups("some-id")


@then('a lineups dict is returned')
def step_assert_lineups_dict(context):
    assert context.result is not None
    assert "lineups" in context.result


def _fake_h2h_row():
    return SimpleNamespace(
        match_id=str(uuid4()), h2h={"total_matches": 0}, captured_at=datetime.now(timezone.utc),
    )


@given('the session get returns a h2h row')
def step_get_returns_h2h_row(context):
    context.session.get.return_value = _fake_h2h_row()


@when('I get the h2h')
def step_get_h2h(context):
    context.result = context.repo.find_h2h("some-id")


@then('a h2h dict is returned')
def step_assert_h2h_dict(context):
    assert context.result is not None
    assert "h2h" in context.result


def _fake_standings_row():
    return SimpleNamespace(
        competition_id=str(uuid4()), standings={"standings": []}, captured_at=datetime.now(timezone.utc),
    )


@given('the session get returns a standings row')
def step_get_returns_standings_row(context):
    context.session.get.return_value = _fake_standings_row()


@when('I get the standings')
def step_get_standings(context):
    context.result = context.repo.find_standings("some-id")


@then('a standings dict is returned')
def step_assert_standings_dict(context):
    assert context.result is not None
    assert "standings" in context.result


def _fake_value_bet_row():
    return SimpleNamespace(
        match_id=str(uuid4()), market="1x2", outcome="HOME", model_probability=Decimal("0.60"),
        bookmaker="bet365", best_odds=Decimal("2.20"), implied_probability=Decimal("0.4545"),
        edge=Decimal("0.1455"), detected_at=datetime.now(timezone.utc),
    )


@given('the session query returns 1 insight row for find_latest_insight')
def step_query_returns_latest_insight(context):
    row = _fake_insight_row()
    chain = context.session.query.return_value.filter.return_value.order_by.return_value
    chain.first.return_value = row


@given('the session query returns no rows for find_latest_insight')
def step_query_returns_no_latest_insight(context):
    chain = context.session.query.return_value.filter.return_value.order_by.return_value
    chain.first.return_value = None


@when('I get the latest insight')
def step_get_latest_insight(context):
    context.result = context.repo.find_latest_insight("some-id")


@then('an insight dict is returned')
def step_assert_insight_dict(context):
    assert context.result is not None
    assert "feature_snapshot" in context.result


@given('the session query returns 1 value bet row')
def step_query_returns_value_bet_row(context):
    row = _fake_value_bet_row()
    context.session.query.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = [row]


@when('I list value bets')
def step_list_value_bets(context):
    context.result = context.repo.find_value_bets()


@then(r'(\d+) value bet dicts? (?:is|are) returned')
def step_assert_n_value_bets(context, count):
    assert len(context.result) == int(count)


def _fake_insight_row():
    return SimpleNamespace(
        id=str(uuid4()), match_id=str(uuid4()), market="match_result", recommendation="favorite:H",
        confidence="0.82", rationale="test", model="v4", feature_snapshot={},
        generated_at=datetime.now(timezone.utc),
    )


@given('the session query returns 1 insight row')
def step_query_returns_insight_row(context):
    row = _fake_insight_row()
    chain = context.session.query.return_value.filter.return_value
    chain.order_by.return_value.limit.return_value.offset.return_value.all.return_value = [row]


@when(r'I list insights for match "([^"]+)"')
def step_list_insights_for_match(context, match_id):
    context.result = context.repo.find_insights(match_id=match_id)


@then(r'(\d+) insight dicts? (?:is|are) returned')
def step_assert_n_insights(context, count):
    assert len(context.result) == int(count)


@when('I list all matches')
def step_list_matches(context):
    context.result = context.repo.find_all_matches()


@when('I get that match')
def step_get_match(context):
    context.result = context.repo.find_match("some-id")


@then(r'(\d+) match dicts? (?:is|are) returned')
def step_assert_n_matches(context, count):
    assert len(context.result) == int(count)


@then('a match dict is returned')
def step_assert_match_dict(context):
    assert context.result is not None
    assert "match_id" in context.result


@then('None is returned')
def step_assert_none(context):
    assert context.result is None


def _fake_value_bet_row_for_get():
    return SimpleNamespace(
        match_id=str(uuid4()), market="1x2", outcome="HOME", model_probability=Decimal("0.60"),
        bookmaker="bet365", best_odds=Decimal("2.20"), implied_probability=Decimal("0.4545"),
        edge=Decimal("0.1455"), detected_at=datetime.now(timezone.utc),
    )


@given('the session get returns a value bet row')
def step_get_returns_value_bet_row(context):
    context.session.get.return_value = _fake_value_bet_row_for_get()


@when('I get the value bet')
def step_get_value_bet(context):
    context.result = context.repo.find_value_bet("some-id", "1x2", "HOME")


@then('a value bet dict is returned')
def step_assert_value_bet_dict(context):
    assert context.result is not None
    assert "edge" in context.result


@when('I insert a value bet outcome')
def step_insert_value_bet_outcome(context):
    context.repo.insert_value_bet_outcome(
        match_id=uuid4(), market="1x2", outcome="HOME", model_probability=Decimal("0.60"),
        bookmaker="bet365", best_odds=Decimal("2.20"), implied_probability=Decimal("0.4545"),
        edge=Decimal("0.1455"), detected_at=datetime.now(timezone.utc),
        resolved_at=datetime.now(timezone.utc), won=True, home_score=2, away_score=0,
    )


@then('a value_bet_outcomes row was added to the session')
def step_assert_value_bet_outcome_added(context):
    context.session.add.assert_called_once()
    added = context.session.add.call_args[0][0]
    assert added.__tablename__ == "value_bet_outcomes", added.__tablename__


def _fake_value_bet_outcome_row():
    return SimpleNamespace(
        id=1, match_id=str(uuid4()), market="1x2", outcome="HOME", model_probability=Decimal("0.60"),
        bookmaker="bet365", best_odds=Decimal("2.20"), implied_probability=Decimal("0.4545"),
        edge=Decimal("0.1455"), detected_at=datetime.now(timezone.utc),
        resolved_at=datetime.now(timezone.utc), won=True, home_score=2, away_score=0,
    )


@given('the session query returns 1 value bet outcome row')
def step_query_returns_value_bet_outcome_row(context):
    row = _fake_value_bet_outcome_row()
    context.session.query.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = [row]


@when('I list value bet outcomes')
def step_list_value_bet_outcomes(context):
    context.result = context.repo.find_value_bet_outcomes()


@then(r'(\d+) value bet outcome dicts? (?:is|are) returned')
def step_assert_n_value_bet_outcomes(context, count):
    assert len(context.result) == int(count)


@given('the session query counts 3 total and 2 won value bet outcomes')
def step_query_counts_outcomes(context):
    context.session.query.return_value.count.return_value = 3
    context.session.query.return_value.filter.return_value.count.return_value = 2


@when('I summarize value bet outcomes')
def step_summarize_value_bet_outcomes(context):
    context.result = context.repo.summarize_value_bet_outcomes()


@then(r'the summary reports (\d+) total, (\d+) won, (\d+) lost')
def step_assert_summary(context, total, won, lost):
    assert context.result == {
        "total": int(total), "won": int(won), "lost": int(lost),
        "win_rate": context.result["win_rate"],
    }
    assert context.result["total"] == int(total)
    assert context.result["won"] == int(won)
    assert context.result["lost"] == int(lost)


def _fake_team_row():
    return SimpleNamespace(
        team_id=str(uuid4()), name="Team ABC", short_name="ABC", country="Brazil", venue_id=12,
    )


@given('the session get returns a team row')
def step_get_returns_team_row(context):
    context.session.get.return_value = _fake_team_row()


@when('I get the team')
def step_get_team(context):
    context.result = context.repo.find_team("some-id")


@then('a team dict is returned')
def step_assert_team_dict(context):
    assert context.result is not None
    assert "name" in context.result


@when('I upsert a venue')
def step_upsert_venue(context):
    context.repo.upsert_venue(
        venue_id="1", name="Maracana", city="Rio de Janeiro", country="Brazil",
        capacity=78000, captured_at=datetime.now(timezone.utc),
    )


def _fake_venue_row():
    return SimpleNamespace(
        venue_id="1", name="Maracana", city="Rio de Janeiro", country="Brazil",
        capacity=78000, captured_at=datetime.now(timezone.utc),
    )


@given('the session get returns a venue row')
def step_get_returns_venue_row(context):
    context.session.get.return_value = _fake_venue_row()


@when('I get the venue')
def step_get_venue(context):
    context.result = context.repo.find_venue("some-id")


@then('a venue dict is returned')
def step_assert_venue_dict(context):
    assert context.result is not None
    assert "name" in context.result


@when('I upsert a referee')
def step_upsert_referee(context):
    context.repo.upsert_referee(
        referee_id="1", name="Ref Name", country="Brazil", details={"cards_per_game": 4.2},
        captured_at=datetime.now(timezone.utc),
    )


def _fake_referee_row():
    return SimpleNamespace(
        referee_id="1", name="Ref Name", country="Brazil", details={"cards_per_game": 4.2},
        captured_at=datetime.now(timezone.utc),
    )


@given('the session get returns a referee row')
def step_get_returns_referee_row(context):
    context.session.get.return_value = _fake_referee_row()


@when('I get the referee')
def step_get_referee(context):
    context.result = context.repo.find_referee("some-id")


@then('a referee dict is returned')
def step_assert_referee_dict(context):
    assert context.result is not None
    assert "name" in context.result


@when('I upsert player stats')
def step_upsert_player_stats(context):
    context.repo.upsert_player_stats(
        match_id=uuid4(), stats={"players": []}, captured_at=datetime.now(timezone.utc),
    )


def _fake_player_stats_row():
    return SimpleNamespace(
        match_id=str(uuid4()), stats={"players": []}, captured_at=datetime.now(timezone.utc),
    )


@given('the session get returns a player stats row')
def step_get_returns_player_stats_row(context):
    context.session.get.return_value = _fake_player_stats_row()


@when('I get the player stats')
def step_get_player_stats(context):
    context.result = context.repo.find_player_stats("some-id")


@then('a player stats dict is returned')
def step_assert_player_stats_dict(context):
    assert context.result is not None
    assert "stats" in context.result


@when('I upsert incidents')
def step_upsert_incidents(context):
    context.repo.upsert_incidents(
        match_id=uuid4(), incidents={"events": []}, captured_at=datetime.now(timezone.utc),
    )


def _fake_incidents_row():
    return SimpleNamespace(
        match_id=str(uuid4()), incidents={"events": []}, captured_at=datetime.now(timezone.utc),
    )


@given('the session get returns an incidents row')
def step_get_returns_incidents_row(context):
    context.session.get.return_value = _fake_incidents_row()


@when('I get the incidents')
def step_get_incidents(context):
    context.result = context.repo.find_incidents("some-id")


@then('an incidents dict is returned')
def step_assert_incidents_dict(context):
    assert context.result is not None
    assert "incidents" in context.result
