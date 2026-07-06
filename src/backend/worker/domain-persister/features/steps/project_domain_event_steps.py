from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

from behave import given, then, use_step_matcher, when

from shared.events import (
    EventMeta,
    MatchFinished,
    MatchScheduled,
    MatchStatus,
    MatchStatusChanged,
    OddsComparisonCaptured,
    OddsSelection,
    OddsSnapshotCaptured,
    PolymarketSnapshotCaptured,
    TeamUpdated,
    SquadMember,
    SquadUpdated,
)
from src.application.project_domain_event import ProjectDomainEventHandler

use_step_matcher("re")


def _meta() -> EventMeta:
    return EventMeta(occurred_at=datetime.now(timezone.utc), producer="acl.bzzoiro", correlation_id=uuid4())


@given('a fresh persister with a mocked read model repository')
def step_fresh_persister(context):
    context.read_models = Mock()
    context.value_bet_detector = Mock()
    context.projector = ProjectDomainEventHandler(context.read_models, context.value_bet_detector)


@when('a MatchScheduled event is processed')
def step_process_scheduled(context):
    event = MatchScheduled(
        meta=_meta(), match_id=uuid4(), competition_id=uuid4(), home_team_id=uuid4(),
        away_team_id=uuid4(), kickoff_at=datetime.now(timezone.utc),
    )
    context.projector.handle(event.model_dump_json().encode())


@when('a MatchStatusChanged event is processed')
def step_process_status(context):
    event = MatchStatusChanged(meta=_meta(), match_id=uuid4(), status=MatchStatus.LIVE, minute=5)
    context.projector.handle(event.model_dump_json().encode())


@when('a MatchFinished event is processed')
def step_process_finished(context):
    event = MatchFinished(meta=_meta(), match_id=uuid4(), home_score=2, away_score=1, statistics={})
    context.projector.handle(event.model_dump_json().encode())


@when('an OddsSnapshotCaptured event is processed')
def step_process_odds(context):
    event = OddsSnapshotCaptured(
        meta=_meta(), match_id=uuid4(), bookmaker="aggregate", market="1x2",
        selections=[OddsSelection(name="home", price="2.10")], captured_at=datetime.now(timezone.utc),
    )
    context.projector.handle(event.model_dump_json().encode())


@when('a TeamUpdated event is processed')
def step_process_team(context):
    event = TeamUpdated(
        meta=_meta(), team_id=uuid4(), name="Team ABC", short_name="ABC", country="Brazil", venue_id=12
    )
    context.projector.handle(event.model_dump_json().encode())


@when('a SquadUpdated event is processed')
def step_process_squad(context):
    event = SquadUpdated(
        meta=_meta(), team_id=uuid4(), members=[
            SquadMember(
                squad_row_id=1, name="Player One", position="ST", status="official",
                club="Club X", club_country="Brazil", age=25
            )
        ]
    )
    context.projector.handle(event.model_dump_json().encode())


@when('an OddsComparisonCaptured event is processed')
def step_process_odds_comparison(context):
    event = OddsComparisonCaptured(
        meta=_meta(), match_id=uuid4(), bookmakers_count=3, total_odds=10,
        markets={"1x2": {"HOME": {"best_odds": 2.1, "best_bookmaker_slug": "bet365", "bookmakers": {}}}},
        captured_at=datetime.now(timezone.utc),
    )
    context.projector.handle(event.model_dump_json().encode())


@when('a PolymarketSnapshotCaptured event is processed')
def step_process_polymarket(context):
    event = PolymarketSnapshotCaptured(
        meta=_meta(), match_id=uuid4(), markets={"1x2": {"HOME": 0.55}},
        captured_at=datetime.now(timezone.utc),
    )
    context.projector.handle(event.model_dump_json().encode())


@when('an object of an unknown event type is projected directly')
def step_process_unknown(context):
    context.error = None
    try:
        context.projector._project(object())
    except Exception as e:
        context.error = e


@then('upsert_match_scheduled was called')
def step_assert_scheduled(context):
    context.read_models.upsert_match_scheduled.assert_called_once()


@then('upsert_match_status was called')
def step_assert_status(context):
    context.read_models.upsert_match_status.assert_called_once()


@then('upsert_match_finished was called')
def step_assert_finished(context):
    context.read_models.upsert_match_finished.assert_called_once()


@then('insert_odds_snapshot was called')
def step_assert_odds(context):
    context.read_models.insert_odds_snapshot.assert_called_once()


@then('upsert_team was called')
def step_assert_team(context):
    context.read_models.upsert_team.assert_called_once()


@then('upsert_squad was called')
def step_assert_squad(context):
    context.read_models.upsert_squad.assert_called_once()


@then('upsert_odds_comparison was called')
def step_assert_odds_comparison(context):
    context.read_models.upsert_odds_comparison.assert_called_once()


@then('upsert_polymarket_snapshot was called')
def step_assert_polymarket(context):
    context.read_models.upsert_polymarket_snapshot.assert_called_once()


@then('the value bet detector evaluated the match after odds comparison')
def step_assert_value_bet_evaluated(context):
    context.value_bet_detector.evaluate.assert_called_once()


@then('the value bet detector was not called')
def step_assert_value_bet_not_called(context):
    context.value_bet_detector.evaluate.assert_not_called()


@then('no read-model method is called and no exception is raised')
def step_assert_noop(context):
    assert context.error is None
    for method_name in (
        "upsert_match_scheduled", "upsert_match_status", "upsert_match_score",
        "upsert_match_finished", "insert_odds_snapshot", "upsert_team", "upsert_squad",
        "upsert_odds_comparison", "upsert_polymarket_snapshot",
    ):
        getattr(context.read_models, method_name).assert_not_called()
