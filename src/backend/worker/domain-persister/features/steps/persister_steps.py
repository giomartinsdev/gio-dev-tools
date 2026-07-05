from __future__ import annotations

from datetime import datetime, timezone
from uuid import NAMESPACE_DNS, uuid4, uuid5

from behave import given, then, use_step_matcher, when

from shared.events import EventMeta, MatchScoreUpdated
from src.application.project_domain_event import ProjectDomainEventHandler

use_step_matcher("re")


class InMemoryReadModelRepository:
    def __init__(self):
        self.matches: dict[str, dict] = {}
        self.odds: dict[str, dict] = {}

    def upsert_match_scheduled(self, match_id, competition_id, home_team_id, away_team_id, kickoff_at, venue):
        self.matches.setdefault(str(match_id), {}).update({
            "competition_id": str(competition_id),
            "home_team_id": str(home_team_id),
            "away_team_id": str(away_team_id),
            "kickoff_at": kickoff_at,
            "venue": venue,
        })

    def upsert_match_status(self, match_id, status, minute):
        self.matches.setdefault(str(match_id), {}).update({"status": status, "minute": minute})

    def upsert_match_score(self, match_id, home_score, away_score, minute):
        self.matches.setdefault(str(match_id), {}).update({
            "home_score": home_score, "away_score": away_score, "minute": minute,
        })

    def upsert_match_finished(self, match_id, home_score, away_score, statistics):
        self.matches.setdefault(str(match_id), {}).update({
            "home_score": home_score, "away_score": away_score, "statistics": statistics, "status": "FINISHED",
        })

    def insert_odds_snapshot(self, event_id, match_id, bookmaker, market, selections, captured_at):
        self.odds[str(event_id)] = {
            "match_id": str(match_id), "bookmaker": bookmaker, "market": market,
            "selections": selections, "captured_at": captured_at,
        }


class InMemoryEventStoreRepository:
    def __init__(self):
        self._seen: set[str] = set()
        self.records: list[dict] = []

    def append(self, event_id: str, event_type: str, occurred_at, payload: dict) -> bool:
        if event_id in self._seen:
            return False
        self._seen.add(event_id)
        self.records.append({"event_id": event_id, "event_type": event_type, "payload": payload})
        return True


def _setup(context):
    context.read_models = InMemoryReadModelRepository()
    context.event_store = InMemoryEventStoreRepository()
    context.projector = ProjectDomainEventHandler(context.read_models)
    context.event_json = None
    context.match_id = None


@given('a fresh persister')
def step_fresh_persister(context):
    _setup(context)


@given(r'a MatchScoreUpdated event for match "([^"]+)" with score (\d+)-(\d+) at minute (\d+)')
def step_score_event(context, match_name, home_score, away_score, minute):
    match_uuid = uuid5(NAMESPACE_DNS, match_name)
    context.match_id = str(match_uuid)
    event = MatchScoreUpdated(
        meta=EventMeta(occurred_at=datetime.now(timezone.utc), producer="acl.bzzoiro", correlation_id=uuid4()),
        match_id=match_uuid,
        home_score=int(home_score),
        away_score=int(away_score),
        minute=int(minute),
    )
    context.event_json = event.model_dump_json()


@when('the persister processes that event')
def step_process_once(context):
    context.projector.handle(context.event_json.encode())


@when(r'the persister processes that event again \(redelivery\)')
def step_process_again(context):
    context.projector.handle(context.event_json.encode())


@then(r'the match read model shows score (\d+)-(\d+)')
def step_assert_score(context, home_score, away_score):
    match = context.read_models.matches[context.match_id]
    assert match["home_score"] == int(home_score)
    assert match["away_score"] == int(away_score)


@then('only one match row exists')
def step_one_match_row(context):
    assert len(context.read_models.matches) == 1, f"expected 1 match row, got {len(context.read_models.matches)}"


@given(r'a raw event store record with event_id "([^"]+)"')
def step_raw_event_store_record(context, event_id):
    context.event_store_event_id = event_id


@when('the event store appends that event_id twice')
def step_append_twice(context):
    now = datetime.now(timezone.utc)
    first = context.event_store.append(context.event_store_event_id, "raw.feed_received", now, {"x": 1})
    second = context.event_store.append(context.event_store_event_id, "raw.feed_received", now, {"x": 1})
    context.append_results = (first, second)


@then('only the first append is recorded')
def step_only_first_recorded(context):
    assert context.append_results == (True, False), f"expected (True, False), got {context.append_results}"
    assert len(context.event_store.records) == 1, f"expected 1 record, got {len(context.event_store.records)}"
