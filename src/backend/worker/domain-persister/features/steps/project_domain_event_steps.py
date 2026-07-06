from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from behave import given, then, use_step_matcher, when

from shared.events import (
    EventMeta,
    H2HCaptured,
    IncidentsCaptured,
    LineupsCaptured,
    MatchFinished,
    MatchScheduled,
    MatchStatus,
    MatchStatusChanged,
    OddsBestCaptured,
    OddsComparisonCaptured,
    OddsSelection,
    OddsSnapshotCaptured,
    PlayerStatsCaptured,
    PolymarketSnapshotCaptured,
    RefereeCaptured,
    StandingsCaptured,
    TeamUpdated,
    SquadMember,
    SquadUpdated,
    VenueCaptured,
)
from src.application.project_domain_event import ProjectDomainEventHandler

use_step_matcher("re")


def _meta() -> EventMeta:
    return EventMeta(occurred_at=datetime.now(timezone.utc), producer="acl.bzzoiro", correlation_id=uuid4())


@given('a fresh persister with a mocked read model repository')
def step_fresh_persister(context):
    context.read_models = Mock()
    context.value_bet_detector = AsyncMock()
    context.value_bet_outcome_resolver = Mock()
    context.projector = ProjectDomainEventHandler(
        context.read_models, context.value_bet_detector, context.value_bet_outcome_resolver,
    )


@when('a MatchScheduled event is processed')
def step_process_scheduled(context):
    event = MatchScheduled(
        meta=_meta(), match_id=uuid4(), competition_id=uuid4(), home_team_id=uuid4(),
        away_team_id=uuid4(), kickoff_at=datetime.now(timezone.utc),
    )
    asyncio.run(context.projector.handle(event.model_dump_json().encode()))


@when('a MatchStatusChanged event is processed')
def step_process_status(context):
    event = MatchStatusChanged(meta=_meta(), match_id=uuid4(), status=MatchStatus.LIVE, minute=5)
    asyncio.run(context.projector.handle(event.model_dump_json().encode()))


@when('a MatchFinished event is processed')
def step_process_finished(context):
    context.error = None
    event = MatchFinished(meta=_meta(), match_id=uuid4(), home_score=2, away_score=1, statistics={})
    try:
        asyncio.run(context.projector.handle(event.model_dump_json().encode()))
    except Exception as e:
        context.error = e


@when('an OddsSnapshotCaptured event is processed')
def step_process_odds(context):
    event = OddsSnapshotCaptured(
        meta=_meta(), match_id=uuid4(), bookmaker="aggregate", market="1x2",
        selections=[OddsSelection(name="home", price="2.10")], captured_at=datetime.now(timezone.utc),
    )
    asyncio.run(context.projector.handle(event.model_dump_json().encode()))


@when('a TeamUpdated event is processed')
def step_process_team(context):
    event = TeamUpdated(
        meta=_meta(), team_id=uuid4(), name="Team ABC", short_name="ABC", country="Brazil", venue_id=12
    )
    asyncio.run(context.projector.handle(event.model_dump_json().encode()))


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
    asyncio.run(context.projector.handle(event.model_dump_json().encode()))


@when('an OddsComparisonCaptured event is processed')
def step_process_odds_comparison(context):
    event = OddsComparisonCaptured(
        meta=_meta(), match_id=uuid4(), bookmakers_count=3, total_odds=10,
        markets={"1x2": {"HOME": {"best_odds": 2.1, "best_bookmaker_slug": "bet365", "bookmakers": {}}}},
        captured_at=datetime.now(timezone.utc),
    )
    asyncio.run(context.projector.handle(event.model_dump_json().encode()))


@when('a PolymarketSnapshotCaptured event is processed')
def step_process_polymarket(context):
    event = PolymarketSnapshotCaptured(
        meta=_meta(), match_id=uuid4(), markets={"1x2": {"HOME": 0.55}},
        captured_at=datetime.now(timezone.utc),
    )
    asyncio.run(context.projector.handle(event.model_dump_json().encode()))


@when('an OddsBestCaptured event is processed')
def step_process_odds_best(context):
    event = OddsBestCaptured(
        meta=_meta(), match_id=uuid4(),
        markets={"1x2": {"HOME": {"best_odds": 2.3, "best_bookmaker_slug": "pinnacle", "bookmakers": {}}}},
        captured_at=datetime.now(timezone.utc),
    )
    asyncio.run(context.projector.handle(event.model_dump_json().encode()))


@when('a LineupsCaptured event is processed')
def step_process_lineups(context):
    event = LineupsCaptured(
        meta=_meta(), match_id=uuid4(), lineup_status="predicted",
        lineups={"home": {"confidence": 0.8}, "away": {"confidence": 0.7}},
        captured_at=datetime.now(timezone.utc),
    )
    asyncio.run(context.projector.handle(event.model_dump_json().encode()))


@when('a H2HCaptured event is processed')
def step_process_h2h(context):
    event = H2HCaptured(
        meta=_meta(), match_id=uuid4(), h2h={"total_matches": 0},
        captured_at=datetime.now(timezone.utc),
    )
    asyncio.run(context.projector.handle(event.model_dump_json().encode()))


@when('a StandingsCaptured event is processed')
def step_process_standings(context):
    event = StandingsCaptured(
        meta=_meta(), competition_id=uuid4(), standings={"standings": []},
        captured_at=datetime.now(timezone.utc),
    )
    asyncio.run(context.projector.handle(event.model_dump_json().encode()))


@when('a VenueCaptured event is processed')
def step_process_venue(context):
    event = VenueCaptured(
        meta=_meta(), venue_id="1", name="Maracana", city="Rio de Janeiro", country="Brazil",
        capacity=78000, captured_at=datetime.now(timezone.utc),
    )
    asyncio.run(context.projector.handle(event.model_dump_json().encode()))


@when('a RefereeCaptured event is processed')
def step_process_referee(context):
    event = RefereeCaptured(
        meta=_meta(), referee_id="1", name="Ref Name", country="Brazil",
        details={"cards_per_game": 4.2}, captured_at=datetime.now(timezone.utc),
    )
    asyncio.run(context.projector.handle(event.model_dump_json().encode()))


@when('a PlayerStatsCaptured event is processed')
def step_process_player_stats(context):
    event = PlayerStatsCaptured(
        meta=_meta(), match_id=uuid4(), stats={"players": []}, captured_at=datetime.now(timezone.utc),
    )
    asyncio.run(context.projector.handle(event.model_dump_json().encode()))


@when('an IncidentsCaptured event is processed')
def step_process_incidents(context):
    event = IncidentsCaptured(
        meta=_meta(), match_id=uuid4(), incidents={"events": []}, captured_at=datetime.now(timezone.utc),
    )
    asyncio.run(context.projector.handle(event.model_dump_json().encode()))


@given('the value bet outcome resolver raises on resolve_match')
def step_resolver_raises(context):
    context.value_bet_outcome_resolver.resolve_match.side_effect = RuntimeError("boom")


@when('an object of an unknown event type is projected directly')
def step_process_unknown(context):
    context.error = None
    try:
        asyncio.run(context.projector._project(object()))
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


@then('merge_odds_comparison_markets was called')
def step_assert_merge_odds_comparison(context):
    context.read_models.merge_odds_comparison_markets.assert_called_once()


@then('upsert_lineups was called')
def step_assert_upsert_lineups(context):
    context.read_models.upsert_lineups.assert_called_once()


@then('upsert_h2h was called')
def step_assert_upsert_h2h(context):
    context.read_models.upsert_h2h.assert_called_once()


@then('upsert_standings was called')
def step_assert_upsert_standings(context):
    context.read_models.upsert_standings.assert_called_once()


@then('the value bet outcome resolver resolved the match')
def step_assert_outcome_resolved(context):
    context.value_bet_outcome_resolver.resolve_match.assert_called_once()


@then('upsert_venue was called')
def step_assert_upsert_venue(context):
    context.read_models.upsert_venue.assert_called_once()


@then('upsert_referee was called')
def step_assert_upsert_referee(context):
    context.read_models.upsert_referee.assert_called_once()


@then('upsert_player_stats was called')
def step_assert_upsert_player_stats(context):
    context.read_models.upsert_player_stats.assert_called_once()


@then('upsert_incidents was called')
def step_assert_upsert_incidents(context):
    context.read_models.upsert_incidents.assert_called_once()


@then('no exception escaped handle')
def step_assert_no_exception(context):
    assert context.error is None


@then('no read-model method is called and no exception is raised')
def step_assert_noop(context):
    assert context.error is None
    for method_name in (
        "upsert_match_scheduled", "upsert_match_status", "upsert_match_score",
        "upsert_match_finished", "insert_odds_snapshot", "upsert_team", "upsert_squad",
        "upsert_odds_comparison", "upsert_polymarket_snapshot",
        "merge_odds_comparison_markets", "upsert_lineups", "upsert_h2h", "upsert_standings",
    ):
        getattr(context.read_models, method_name).assert_not_called()
