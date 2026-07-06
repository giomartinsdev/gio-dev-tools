from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.transaction_manager import TransactionManager

from .models import (
    H2HModel,
    InsightModel,
    LineupsModel,
    MatchModel,
    OddsComparisonModel,
    OddsSnapshotModel,
    PolymarketSnapshotModel,
    SquadMemberModel,
    StandingsModel,
    TeamModel,
    ValueBetModel,
)


class ReadModelRepository:
    def upsert_match_scheduled(
        self,
        match_id: UUID,
        competition_id: UUID,
        home_team_id: UUID,
        away_team_id: UUID,
        kickoff_at: datetime,
        venue: Optional[str],
    ) -> None:
        stmt = pg_insert(MatchModel).values(
            match_id=str(match_id),
            competition_id=str(competition_id),
            home_team_id=str(home_team_id),
            away_team_id=str(away_team_id),
            kickoff_at=kickoff_at,
            venue=venue,
            status="SCHEDULED",
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["match_id"],
            set_={
                "competition_id": stmt.excluded.competition_id,
                "home_team_id": stmt.excluded.home_team_id,
                "away_team_id": stmt.excluded.away_team_id,
                "kickoff_at": stmt.excluded.kickoff_at,
                "venue": stmt.excluded.venue,
            },
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def upsert_match_status(self, match_id: UUID, status: str, minute: Optional[int]) -> None:
        stmt = pg_insert(MatchModel).values(match_id=str(match_id), status=status, minute=minute)
        stmt = stmt.on_conflict_do_update(
            index_elements=["match_id"],
            set_={"status": stmt.excluded.status, "minute": stmt.excluded.minute},
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def upsert_match_score(self, match_id: UUID, home_score: int, away_score: int, minute: int) -> None:
        stmt = pg_insert(MatchModel).values(
            match_id=str(match_id), home_score=home_score, away_score=away_score, minute=minute,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["match_id"],
            set_={
                "home_score": stmt.excluded.home_score,
                "away_score": stmt.excluded.away_score,
                "minute": stmt.excluded.minute,
            },
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def upsert_match_finished(self, match_id: UUID, home_score: int, away_score: int, statistics: dict) -> None:
        stmt = pg_insert(MatchModel).values(
            match_id=str(match_id),
            status="FINISHED",
            home_score=home_score,
            away_score=away_score,
            statistics=statistics,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["match_id"],
            set_={
                "status": stmt.excluded.status,
                "home_score": stmt.excluded.home_score,
                "away_score": stmt.excluded.away_score,
                "statistics": stmt.excluded.statistics,
            },
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def insert_odds_snapshot(
        self,
        event_id: UUID,
        match_id: UUID,
        bookmaker: str,
        market: str,
        selections: list[dict],
        captured_at: datetime,
    ) -> None:
        stmt = pg_insert(OddsSnapshotModel).values(
            id=str(event_id),
            match_id=str(match_id),
            bookmaker=bookmaker,
            market=market,
            selections=selections,
            captured_at=captured_at,
        ).on_conflict_do_nothing(index_elements=["id"])
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def insert_insight(
        self,
        insight_id: UUID,
        match_id: UUID,
        market: str,
        recommendation: str,
        confidence: Decimal,
        rationale: str,
        model: str,
        feature_snapshot: dict,
        generated_at: datetime,
    ) -> None:
        stmt = pg_insert(InsightModel).values(
            id=str(insight_id),
            match_id=str(match_id),
            market=market,
            recommendation=recommendation,
            confidence=confidence,
            rationale=rationale,
            model=model,
            feature_snapshot=feature_snapshot,
            generated_at=generated_at,
        ).on_conflict_do_nothing(index_elements=["id"])
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def upsert_team(
        self,
        team_id: UUID,
        name: str,
        short_name: str,
        country: str,
        venue_id: Optional[int],
    ) -> None:
        stmt = pg_insert(TeamModel).values(
            team_id=str(team_id),
            name=name,
            short_name=short_name,
            country=country,
            venue_id=venue_id,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["team_id"],
            set_={
                "name": stmt.excluded.name,
                "short_name": stmt.excluded.short_name,
                "country": stmt.excluded.country,
                "venue_id": stmt.excluded.venue_id,
            },
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def upsert_squad(
        self,
        team_id: UUID,
        members: list[SquadMember],
    ) -> None:
        from shared.events import SquadMember
        with TransactionManager.get().session() as s:
            # 1. Clean previous squad members for this team
            s.query(SquadMemberModel).filter(SquadMemberModel.team_id == str(team_id)).delete()
            
            # 2. Insert new squad members using bulk insert or loop
            for member in members:
                model_member = SquadMemberModel(
                    squad_row_id=member.squad_row_id,
                    team_id=str(team_id),
                    player_id=str(member.player_id) if member.player_id else None,
                    name=member.name,
                    jersey_number=member.jersey_number,
                    position=member.position,
                    status=member.status,
                    club=member.club,
                    club_country=member.club_country,
                    caps=member.caps,
                    goals=member.goals,
                    age=member.age,
                    date_of_birth=member.date_of_birth,
                )
                s.add(model_member)


    def upsert_odds_comparison(
        self,
        match_id: UUID,
        bookmakers_count: int,
        total_odds: int,
        markets: dict,
        captured_at: datetime,
    ) -> None:
        stmt = pg_insert(OddsComparisonModel).values(
            match_id=str(match_id),
            bookmakers_count=bookmakers_count,
            total_odds=total_odds,
            markets=markets,
            captured_at=captured_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["match_id"],
            set_={
                "bookmakers_count": stmt.excluded.bookmakers_count,
                "total_odds": stmt.excluded.total_odds,
                "markets": stmt.excluded.markets,
                "captured_at": stmt.excluded.captured_at,
            },
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def merge_odds_comparison_markets(
        self,
        match_id: UUID,
        markets_patch: dict,
        captured_at: datetime,
    ) -> None:
        """Partial update for OddsBestCaptured (a cheap, 1x2-only feed): the
        JSONB `||` concat operator merges `markets_patch`'s top-level keys
        into the existing row's `markets` in a single atomic statement — no
        read-then-write race, and any other market key (over_under, btts)
        a fuller OddsComparisonCaptured already wrote is left untouched.
        On first insert for a match (no existing row), `markets_patch`
        alone becomes the row's `markets` — bookmakers_count/total_odds
        default to 0 since this feed doesn't report per-market bookmaker
        counts; a later full comparison poll overwrites them properly."""
        stmt = pg_insert(OddsComparisonModel).values(
            match_id=str(match_id),
            bookmakers_count=0,
            total_odds=0,
            markets=markets_patch,
            captured_at=captured_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["match_id"],
            set_={
                "markets": OddsComparisonModel.markets.op("||")(stmt.excluded.markets),
                "captured_at": stmt.excluded.captured_at,
            },
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def upsert_polymarket_snapshot(self, match_id: UUID, markets: dict, captured_at: datetime) -> None:
        stmt = pg_insert(PolymarketSnapshotModel).values(
            match_id=str(match_id), markets=markets, captured_at=captured_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["match_id"],
            set_={"markets": stmt.excluded.markets, "captured_at": stmt.excluded.captured_at},
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def find_odds_comparison(self, match_id: str) -> Optional[dict]:
        with TransactionManager.get().read_only() as s:
            row = s.get(OddsComparisonModel, match_id)
            return _odds_comparison_to_dict(row) if row else None

    def upsert_lineups(self, match_id: UUID, lineup_status: str, lineups: dict, captured_at: datetime) -> None:
        stmt = pg_insert(LineupsModel).values(
            match_id=str(match_id), lineup_status=lineup_status, lineups=lineups, captured_at=captured_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["match_id"],
            set_={
                "lineup_status": stmt.excluded.lineup_status,
                "lineups": stmt.excluded.lineups,
                "captured_at": stmt.excluded.captured_at,
            },
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def find_lineups(self, match_id: str) -> Optional[dict]:
        with TransactionManager.get().read_only() as s:
            row = s.get(LineupsModel, match_id)
            return _lineups_to_dict(row) if row else None

    def upsert_h2h(self, match_id: UUID, h2h: dict, captured_at: datetime) -> None:
        stmt = pg_insert(H2HModel).values(match_id=str(match_id), h2h=h2h, captured_at=captured_at)
        stmt = stmt.on_conflict_do_update(
            index_elements=["match_id"],
            set_={"h2h": stmt.excluded.h2h, "captured_at": stmt.excluded.captured_at},
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def find_h2h(self, match_id: str) -> Optional[dict]:
        with TransactionManager.get().read_only() as s:
            row = s.get(H2HModel, match_id)
            return _h2h_to_dict(row) if row else None

    def upsert_standings(self, competition_id: UUID, standings: dict, captured_at: datetime) -> None:
        stmt = pg_insert(StandingsModel).values(
            competition_id=str(competition_id), standings=standings, captured_at=captured_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["competition_id"],
            set_={"standings": stmt.excluded.standings, "captured_at": stmt.excluded.captured_at},
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def find_standings(self, competition_id: str) -> Optional[dict]:
        with TransactionManager.get().read_only() as s:
            row = s.get(StandingsModel, competition_id)
            return _standings_to_dict(row) if row else None

    def find_latest_insight(self, match_id: str) -> Optional[dict]:
        with TransactionManager.get().read_only() as s:
            row = (
                s.query(InsightModel)
                .filter(InsightModel.match_id == match_id)
                .order_by(InsightModel.generated_at.desc())
                .first()
            )
            return _insight_to_dict(row) if row else None

    def upsert_value_bet(
        self,
        match_id: UUID,
        market: str,
        outcome: str,
        model_probability: Decimal,
        bookmaker: str,
        best_odds: Decimal,
        implied_probability: Decimal,
        edge: Decimal,
        detected_at: datetime,
    ) -> None:
        stmt = pg_insert(ValueBetModel).values(
            match_id=str(match_id),
            market=market,
            outcome=outcome,
            model_probability=model_probability,
            bookmaker=bookmaker,
            best_odds=best_odds,
            implied_probability=implied_probability,
            edge=edge,
            detected_at=detected_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["match_id", "market", "outcome"],
            set_={
                "model_probability": stmt.excluded.model_probability,
                "bookmaker": stmt.excluded.bookmaker,
                "best_odds": stmt.excluded.best_odds,
                "implied_probability": stmt.excluded.implied_probability,
                "edge": stmt.excluded.edge,
                "detected_at": stmt.excluded.detected_at,
            },
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def delete_value_bet(self, match_id: UUID, market: str, outcome: str) -> None:
        with TransactionManager.get().session() as s:
            s.query(ValueBetModel).filter(
                ValueBetModel.match_id == str(match_id),
                ValueBetModel.market == market,
                ValueBetModel.outcome == outcome,
            ).delete()

    def find_value_bets(
        self, match_id: Optional[str] = None, limit: int = 50, offset: int = 0,
    ) -> list[dict]:
        with TransactionManager.get().read_only() as s:
            q = s.query(ValueBetModel)
            if match_id is not None:
                q = q.filter(ValueBetModel.match_id == match_id)
            rows = q.order_by(ValueBetModel.edge.desc()).limit(limit).offset(offset).all()
            return [_value_bet_to_dict(r) for r in rows]

    def find_insights(self, match_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> list[dict]:
        with TransactionManager.get().read_only() as s:
            q = s.query(InsightModel)
            if match_id is not None:
                q = q.filter(InsightModel.match_id == match_id)
            rows = q.order_by(InsightModel.generated_at.desc()).limit(limit).offset(offset).all()
            return [_insight_to_dict(r) for r in rows]

    def find_all_matches(self, limit: int = 50, offset: int = 0) -> list[dict]:
        with TransactionManager.get().read_only() as s:
            rows = (
                s.query(MatchModel)
                .order_by(MatchModel.updated_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            return [_match_to_dict(r) for r in rows]

    def find_match(self, match_id: str) -> Optional[dict]:
        with TransactionManager.get().read_only() as s:
            row = s.get(MatchModel, match_id)
            return _match_to_dict(row) if row else None


def _match_to_dict(row: MatchModel) -> dict:
    return {
        "match_id": row.match_id,
        "competition_id": row.competition_id,
        "home_team_id": row.home_team_id,
        "away_team_id": row.away_team_id,
        "status": row.status,
        "home_score": row.home_score,
        "away_score": row.away_score,
        "minute": row.minute,
        "kickoff_at": row.kickoff_at.isoformat() if row.kickoff_at else None,
        "venue": row.venue,
        "statistics": row.statistics,
    }


def _insight_to_dict(row: InsightModel) -> dict:
    return {
        "id": row.id,
        "match_id": row.match_id,
        "market": row.market,
        "recommendation": row.recommendation,
        "confidence": str(row.confidence),
        "rationale": row.rationale,
        "model": row.model,
        "feature_snapshot": row.feature_snapshot,
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
    }


def _odds_comparison_to_dict(row: OddsComparisonModel) -> dict:
    return {
        "match_id": row.match_id,
        "bookmakers_count": row.bookmakers_count,
        "total_odds": row.total_odds,
        "markets": row.markets,
        "captured_at": row.captured_at.isoformat() if row.captured_at else None,
    }


def _value_bet_to_dict(row: ValueBetModel) -> dict:
    return {
        "match_id": row.match_id,
        "market": row.market,
        "outcome": row.outcome,
        "model_probability": str(row.model_probability),
        "bookmaker": row.bookmaker,
        "best_odds": str(row.best_odds),
        "implied_probability": str(row.implied_probability),
        "edge": str(row.edge),
        "detected_at": row.detected_at.isoformat() if row.detected_at else None,
    }


def _lineups_to_dict(row: LineupsModel) -> dict:
    return {
        "match_id": row.match_id,
        "lineup_status": row.lineup_status,
        "lineups": row.lineups,
        "captured_at": row.captured_at.isoformat() if row.captured_at else None,
    }


def _h2h_to_dict(row: H2HModel) -> dict:
    return {
        "match_id": row.match_id,
        "h2h": row.h2h,
        "captured_at": row.captured_at.isoformat() if row.captured_at else None,
    }


def _standings_to_dict(row: StandingsModel) -> dict:
    return {
        "competition_id": row.competition_id,
        "standings": row.standings,
        "captured_at": row.captured_at.isoformat() if row.captured_at else None,
    }
