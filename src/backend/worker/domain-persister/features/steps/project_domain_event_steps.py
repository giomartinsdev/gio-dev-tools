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
    OddsSelection,
    OddsSnapshotCaptured,
    TeamUpdated,
)
from src.application.project_domain_event import ProjectDomainEventHandler

use_step_matcher("re")


def _meta() -> EventMeta:
    return EventMeta(occurred_at=datetime.now(timezone.utc), producer="acl.bzzoiro", correlation_id=uuid4())


@given('a fresh persister with a mocked read model repository')
def step_fresh_persister(context):
    context.read_models = Mock()
    context.projector = ProjectDomainEventHandler(context.read_models)


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
        meta=_meta(), team_id=uuid4(), name="Team ABC", code="ABC", logo="http://logo"
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


@then('no read-model method is called and no exception is raised')
def step_assert_noop(context):
    assert context.error is None
    for method_name in (
        "upsert_match_scheduled", "upsert_match_status", "upsert_match_score",
        "upsert_match_finished", "insert_odds_snapshot", "upsert_team",
    ):
        getattr(context.read_models, method_name).assert_not_called()
