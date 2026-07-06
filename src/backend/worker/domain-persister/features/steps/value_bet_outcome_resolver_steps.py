from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from behave import given, then, use_step_matcher, when

from src.application.value_bet_outcome_resolver import ValueBetOutcomeResolver

use_step_matcher("re")


class _FakeReadModelRepository:
    def __init__(self):
        self.open_bets: list[dict] = []
        self.archived: list[dict] = []
        self.deleted: list[tuple] = []

    def find_value_bets(self, match_id):
        return self.open_bets

    def insert_value_bet_outcome(self, match_id, market, outcome, model_probability, bookmaker,
                                  best_odds, implied_probability, edge, detected_at, resolved_at,
                                  won, home_score, away_score):
        self.archived.append({
            "match_id": str(match_id), "market": market, "outcome": outcome, "won": won,
            "home_score": home_score, "away_score": away_score,
        })

    def delete_value_bet(self, match_id, market, outcome):
        self.deleted.append((str(match_id), market, outcome))
        self.open_bets = [b for b in self.open_bets if not (b["market"] == market and b["outcome"] == outcome)]


def _fake_bet(market: str, outcome: str) -> dict:
    return {
        "market": market,
        "outcome": outcome,
        "model_probability": "0.60",
        "bookmaker": "bet365",
        "best_odds": "2.20",
        "implied_probability": "0.4545",
        "edge": "0.1455",
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }


@given('a fresh value bet outcome resolver')
def step_fresh_resolver(context):
    context.match_id = uuid4()
    context.read_models = _FakeReadModelRepository()
    context.resolver = ValueBetOutcomeResolver(context.read_models)


@given('the match has no open value bets')
def step_no_open_bets(context):
    context.read_models.open_bets = []


@given(r'an open value bet for "([^"]+)" "([^"]+)"')
def step_open_bet(context, market, outcome):
    context.read_models.open_bets.append(_fake_bet(market, outcome))


@when(r'the match finishes (\d+)-(\d+)')
def step_match_finishes(context, home_score, away_score):
    context.resolver.resolve_match(context.match_id, int(home_score), int(away_score))


@then('no value bet outcome is archived')
def step_assert_no_outcome(context):
    assert context.read_models.archived == [], context.read_models.archived


@then(r'the value bet outcome for "([^"]+)" "([^"]+)" is archived as (won|lost)')
def step_assert_outcome(context, market, outcome, expected):
    matches = [
        a for a in context.read_models.archived
        if a["market"] == market and a["outcome"] == outcome
    ]
    assert matches, context.read_models.archived
    expected_won = expected == "won"
    assert matches[0]["won"] == expected_won, matches[0]


@then(r'the value bet for "([^"]+)" "([^"]+)" is no longer open')
def step_assert_no_longer_open(context, market, outcome):
    remaining = [b for b in context.read_models.open_bets if b["market"] == market and b["outcome"] == outcome]
    assert remaining == [], remaining
    assert (str(context.match_id), market, outcome) in context.read_models.deleted
