from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

from behave import given, then, use_step_matcher, when

from shared.events import EventMeta, InsightGenerated
from src.application.project_insight import ProjectInsightHandler
from src.application.queries.list_insights import ListInsightsHandler, ListInsightsQuery
from src.application.queries.list_value_bets import ListValueBetsHandler, ListValueBetsQuery

use_step_matcher("re")


@given('a fresh insight projector with a mocked read model repository')
def step_fresh_insight_projector(context):
    context.read_models = Mock()
    context.value_bet_detector = Mock()
    context.projector = ProjectInsightHandler(context.read_models, context.value_bet_detector)
    context.event = InsightGenerated(
        meta=EventMeta(occurred_at=datetime.now(timezone.utc), producer="acl.bzzoiro", correlation_id=uuid4()),
        insight_id=uuid4(), match_id=uuid4(), market="match_result", recommendation="favorite:H",
        confidence="0.82", rationale="test", model="v4", feature_snapshot={"a": 1},
        generated_at=datetime.now(timezone.utc),
    )


@when('an InsightGenerated event is processed')
def step_process_insight(context):
    context.projector.handle(context.event.model_dump_json().encode())


@then("insert_insight was called with the event's fields")
def step_assert_insert_insight_called(context):
    context.read_models.insert_insight.assert_called_once_with(
        insight_id=context.event.insight_id,
        match_id=context.event.match_id,
        market=context.event.market,
        recommendation=context.event.recommendation,
        confidence=context.event.confidence,
        rationale=context.event.rationale,
        model=context.event.model,
        feature_snapshot=context.event.feature_snapshot,
        generated_at=context.event.generated_at,
    )


@then('the value bet detector evaluated the match')
def step_assert_value_bet_evaluated(context):
    context.value_bet_detector.evaluate.assert_called_once_with(context.event.match_id)


@given('a fake read model repository for insights')
def step_fake_repo_for_insights(context):
    context.repo = Mock()
    context.repo.find_insights.return_value = [{"id": "1"}]


@when(r'I list insights with limit (\d+) and offset (\d+)')
def step_list_insights_paged(context, limit, offset):
    context.result = ListInsightsHandler(context.repo).handle(
        ListInsightsQuery(limit=int(limit), offset=int(offset))
    )


@then(r'find_insights was called with match_id None limit (\d+) and offset (\d+)')
def step_assert_find_insights_called(context, limit, offset):
    context.repo.find_insights.assert_called_once_with(match_id=None, limit=int(limit), offset=int(offset))


@given('a fake read model repository for value bets')
def step_fake_repo_for_value_bets(context):
    context.repo = Mock()
    context.repo.find_value_bets.return_value = [{"match_id": "1"}]


@when(r'I list value bets with limit (\d+) and offset (\d+)')
def step_list_value_bets_paged(context, limit, offset):
    context.result = ListValueBetsHandler(context.repo).handle(
        ListValueBetsQuery(limit=int(limit), offset=int(offset))
    )


@then(r'find_value_bets was called with match_id None limit (\d+) and offset (\d+)')
def step_assert_find_value_bets_called(context, limit, offset):
    context.repo.find_value_bets.assert_called_once_with(match_id=None, limit=int(limit), offset=int(offset))
