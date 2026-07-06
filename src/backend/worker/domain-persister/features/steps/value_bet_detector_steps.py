from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from behave import given, then, use_step_matcher, when

from src.application.value_bet_detector import ValueBetDetector

use_step_matcher("re")


class _FakeReadModelRepository:
    def __init__(self):
        self.insight: dict | None = None
        self.comparison: dict | None = None
        self.lineups: dict | None = None
        self.value_bets: dict[tuple, dict] = {}

    def find_latest_insight(self, match_id):
        return self.insight

    def find_odds_comparison(self, match_id):
        return self.comparison

    def find_value_bet(self, match_id, market, outcome):
        return self.value_bets.get((str(match_id), market, outcome))

    def find_lineups(self, match_id):
        return self.lineups

    def find_match(self, match_id):
        return None

    def find_team(self, team_id):
        return None

    def upsert_value_bet(self, match_id, market, outcome, model_probability, bookmaker,
                          best_odds, implied_probability, edge, detected_at):
        self.value_bets[(str(match_id), market, outcome)] = {
            "model_probability": model_probability,
            "bookmaker": bookmaker,
            "best_odds": best_odds,
            "implied_probability": implied_probability,
            "edge": edge,
        }

    def delete_value_bet(self, match_id, market, outcome):
        self.value_bets.pop((str(match_id), market, outcome), None)


def _outcome_entry(best_odds: str) -> dict:
    return {"best_odds": float(best_odds), "best_bookmaker_slug": "bet365", "bookmakers": {}}


@given('a fresh value bet detector')
def step_fresh_detector(context):
    context.match_id = uuid4()
    context.read_models = _FakeReadModelRepository()
    context.detector = ValueBetDetector(context.read_models, edge_threshold=Decimal("0.05"))


@given('a fresh value bet detector with a notifier')
def step_fresh_detector_with_notifier(context):
    context.match_id = uuid4()
    context.read_models = _FakeReadModelRepository()
    context.notifier = AsyncMock()
    context.detector = ValueBetDetector(
        context.read_models, edge_threshold=Decimal("0.05"), notifier=context.notifier,
    )


@given('a fresh value bet detector with a notifier that raises on notify')
def step_fresh_detector_with_failing_notifier(context):
    context.match_id = uuid4()
    context.read_models = _FakeReadModelRepository()
    context.notifier = AsyncMock()
    context.notifier.notify.side_effect = RuntimeError("boom")
    context.detector = ValueBetDetector(
        context.read_models, edge_threshold=Decimal("0.05"), notifier=context.notifier,
    )


@given(r'an insight exists with match_result prob_home ([\d.]+)')
def step_insight_match_result(context, prob_home):
    context.read_models.insight = {
        "feature_snapshot": {"match_result": {"prob_home": prob_home}},
    }


@given(r'an insight exists with match_result prob_home ([\d.]+) and over_under prob_over_25 ([\d.]+)')
def step_insight_two_markets(context, prob_home, prob_over_25):
    context.read_models.insight = {
        "feature_snapshot": {
            "match_result": {"prob_home": prob_home},
            "over_under": {"prob_over_25": prob_over_25},
        },
    }


@given(r'odds comparison data exists for the match with best odds ([\d.]+) on "([^"]+)" "([^"]+)"')
def step_odds_comparison_one_market(context, best_odds, market, outcome):
    context.read_models.comparison = {
        "markets": {market: {outcome: _outcome_entry(best_odds)}},
    }


@given(
    r'odds comparison data exists for the match with best odds ([\d.]+) on "([^"]+)" "([^"]+)" '
    r'and best odds ([\d.]+) on "([^"]+)" "([^"]+)"'
)
def step_odds_comparison_two_markets(context, odds_a, market_a, outcome_a, odds_b, market_b, outcome_b):
    context.read_models.comparison = {
        "markets": {
            market_a: {outcome_a: _outcome_entry(odds_a)},
            market_b: {outcome_b: _outcome_entry(odds_b)},
        },
    }


@given(r'a predicted lineup exists with confidence ([\d.]+) for both sides')
def step_lineup_both_sides(context, confidence):
    context.read_models.lineups = {
        "lineup_status": "predicted",
        "lineups": {
            "home": {"confidence": float(confidence)},
            "away": {"confidence": float(confidence)},
        },
    }


@given(r'a predicted lineup exists with home confidence ([\d.]+) and away confidence ([\d.]+)')
def step_lineup_per_side(context, home_confidence, away_confidence):
    context.read_models.lineups = {
        "lineup_status": "predicted",
        "lineups": {
            "home": {"confidence": float(home_confidence)},
            "away": {"confidence": float(away_confidence)},
        },
    }


@given('the detector already evaluated the match once')
def step_already_evaluated(context):
    asyncio.run(context.detector.evaluate(context.match_id))
    assert context.read_models.value_bets, "expected a value bet to exist before the odds move"


@when(r'the odds move to best odds ([\d.]+) on "([^"]+)" "([^"]+)"')
def step_odds_move(context, best_odds, market, outcome):
    context.read_models.comparison["markets"][market][outcome] = _outcome_entry(best_odds)


@when('the detector evaluates the match')
def step_evaluate(context):
    asyncio.run(context.detector.evaluate(context.match_id))


@then('no value bet is recorded')
def step_assert_no_value_bet(context):
    assert context.read_models.value_bets == {}, context.read_models.value_bets


@then(r'no value bet is recorded for "([^"]+)" "([^"]+)"')
def step_assert_no_value_bet_for(context, market, outcome):
    key = (str(context.match_id), market, outcome)
    assert key not in context.read_models.value_bets, context.read_models.value_bets


@then(r'a value bet is recorded for "([^"]+)" "([^"]+)" with edge close to ([\d.]+)')
def step_assert_value_bet(context, market, outcome, expected_edge):
    key = (str(context.match_id), market, outcome)
    assert key in context.read_models.value_bets, context.read_models.value_bets
    edge = context.read_models.value_bets[key]["edge"]
    assert abs(edge - Decimal(expected_edge)) < Decimal("0.001"), f"expected ~{expected_edge}, got {edge}"


@then('the notifier sent an alert')
def step_assert_notifier_sent(context):
    context.notifier.notify.assert_awaited_once()


@then('the notifier was not called again')
def step_assert_notifier_not_called_again(context):
    assert context.notifier.notify.await_count == 1, context.notifier.notify.await_count
