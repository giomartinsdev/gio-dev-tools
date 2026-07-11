from __future__ import annotations

from datetime import date

from behave import given, then, use_step_matcher, when

from src.domain.report import filter_by_reference_day, format_report, group_value_bets_by_match

use_step_matcher("re")


def _value_bet(match_id="m1", day="2026-07-12", market="1x2", outcome="HOME", edge="0.05"):
    return {
        "match_id": match_id,
        "market": market,
        "outcome": outcome,
        "model_probability": "0.5",
        "bookmaker": "pinnacle",
        "best_odds": "2.5",
        "implied_probability": "0.4",
        "edge": edge,
        "detected_at": f"{day}T12:00:00+00:00",
        "kickoff_at": f"{day}T15:00:00+00:00",
        "status": "SCHEDULED",
        "home_team_name": "Team A",
        "away_team_name": "Team B",
    }


@given('value bets on "([^"]+)" and "([^"]+)"')
def step_value_bets_two_days(context, day1, day2):
    context.value_bets = [_value_bet(match_id="m1", day=day1), _value_bet(match_id="m2", day=day2)]
    context.day1 = day1
    context.day2 = day2


@given(r'(\d+) value bets? for match "([^"]+)" and (\d+) value bets? for match "([^"]+)"')
def step_value_bets_two_matches(context, count1, match1, count2, match2):
    context.value_bets = (
        [_value_bet(match_id=match1) for _ in range(int(count1))]
        + [_value_bet(match_id=match2) for _ in range(int(count2))]
    )


@given(r'(\d+) value bets? for match "([^"]+)" with market "([^"]+)", outcome "([^"]+)", edge "([^"]+)"')
def step_value_bet_with_market(context, count, match_id, market, outcome, edge):
    context.value_bets = [
        _value_bet(match_id=match_id, market=market, outcome=outcome, edge=edge) for _ in range(int(count))
    ]


@given('no value bets')
def step_no_value_bets(context):
    context.value_bets = []


@when('I filter by reference day "([^"]+)"')
def step_filter(context, reference_day):
    context.result = filter_by_reference_day(context.value_bets, date.fromisoformat(reference_day))


@when('I group value bets by match')
def step_group(context):
    context.groups = group_value_bets_by_match(context.value_bets)


@when('I format the report for "([^"]+)"')
def step_format(context, reference_day):
    context.report = format_report(context.value_bets, date.fromisoformat(reference_day))


@then('only the "([^"]+)" value bets remain')
def step_assert_filtered(context, day):
    assert len(context.result) == 1, context.result
    assert context.result[0]["kickoff_at"].startswith(day), context.result


@then(r'there are (\d+) groups?')
def step_assert_group_count(context, count):
    assert len(context.groups) == int(count), context.groups


@then(r'group "([^"]+)" has (\d+) value bets?')
def step_assert_group_size(context, match_id, count):
    assert len(context.groups[match_id]) == int(count), context.groups


@then('the report contains "([^"]+)"')
def step_assert_report_contains(context, fragment):
    assert fragment in context.report, context.report
