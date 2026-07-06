from __future__ import annotations

from behave import given, then, use_step_matcher, when

use_step_matcher("re")


@given(r'a squad payload for team (\d+) with a minimal player entry')
def step_minimal_squad_payload(context, team_ref_id):
    context.team_ref_id = int(team_ref_id)
    context.squad_payloads = [{
        "id": 17456,
        "name": "Marcelo Ajul",
        "short_name": "M. Ajul",
        "position": "D",
        "jersey_number": 3,
        "nationality": "Brazil",
        "date_of_birth": "2002-08-26",
    }]


@given(r'a squad payload for team (\d+) with a fully populated player entry')
def step_full_squad_payload(context, team_ref_id):
    context.team_ref_id = int(team_ref_id)
    context.squad_payloads = [{
        "id": 17456,
        "name": "Marcelo Ajul",
        "jersey_number": 3,
        "position": "D",
        "status": "official",
        "club": "Club X",
        "club_country": "Brazil",
        "caps": 5,
        "goals": 1,
        "date_of_birth": "2002-08-26",
        "age": 26,
    }]


@when('I translate the squad')
def step_translate_squad(context):
    context.squad_event = context.translator.translate_squad(context.team_ref_id, context.squad_payloads)


@then(r'the squad member has status "([^"]*)", club "([^"]*)" and club_country "([^"]*)"')
def step_assert_squad_member_fields(context, status, club, club_country):
    member = context.squad_event.members[0]
    assert member.status == status, member.status
    assert member.club == club, member.club
    assert member.club_country == club_country, member.club_country


@then("the squad member's player_id is resolved from the player's own provider id")
def step_assert_player_id_resolved(context):
    member = context.squad_event.members[0]
    expected = context.identity_repo.get_or_create("bzzoiro", "17456", "player")
    assert member.player_id == expected, (member.player_id, expected)
