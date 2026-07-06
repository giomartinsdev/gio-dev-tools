from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.transaction_manager import TransactionManager

from .models import (
    H2HModel,
    IncidentsModel,
    InsightModel,
    LineupsModel,
    MatchModel,
    OddsComparisonModel,
    OddsSnapshotModel,
    PlayerStatsModel,
    PolymarketSnapshotModel,
    RefereeModel,
    SquadMemberModel,
    StandingsModel,
    TeamModel,
    ValueBetModel,
    ValueBetOutcomeModel,
    VenueModel,
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

    def find_value_bet(self, match_id: str, market: str, outcome: str) -> Optional[dict]:
        """Single-key lookup, used to tell a brand-new value bet (worth
        alerting on) apart from re-confirming one already known."""
        with TransactionManager.get().read_only() as s:
            row = s.get(ValueBetModel, (match_id, market, outcome))
            return _value_bet_to_dict(row) if row else None

    def insert_value_bet_outcome(
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
        resolved_at: datetime,
        won: bool,
        home_score: int,
        away_score: int,
    ) -> None:
        with TransactionManager.get().session() as s:
            s.add(ValueBetOutcomeModel(
                match_id=str(match_id),
                market=market,
                outcome=outcome,
                model_probability=model_probability,
                bookmaker=bookmaker,
                best_odds=best_odds,
                implied_probability=implied_probability,
                edge=edge,
                detected_at=detected_at,
                resolved_at=resolved_at,
                won=won,
                home_score=home_score,
                away_score=away_score,
            ))

    def find_value_bet_outcomes(
        self, match_id: Optional[str] = None, limit: int = 50, offset: int = 0,
    ) -> list[dict]:
        with TransactionManager.get().read_only() as s:
            q = s.query(ValueBetOutcomeModel)
            if match_id is not None:
                q = q.filter(ValueBetOutcomeModel.match_id == match_id)
            rows = q.order_by(ValueBetOutcomeModel.resolved_at.desc()).limit(limit).offset(offset).all()
            return [_value_bet_outcome_to_dict(r) for r in rows]

    def summarize_value_bet_outcomes(self) -> dict:
        with TransactionManager.get().read_only() as s:
            total = s.query(ValueBetOutcomeModel).count()
            won = s.query(ValueBetOutcomeModel).filter(ValueBetOutcomeModel.won.is_(True)).count()
        return {
            "total": total,
            "won": won,
            "lost": total - won,
            "win_rate": (won / total) if total else None,
        }

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

    def find_team(self, team_id: str) -> Optional[dict]:
        with TransactionManager.get().read_only() as s:
            row = s.get(TeamModel, team_id)
            return _team_to_dict(row) if row else None

    def upsert_venue(
        self,
        venue_id: str,
        name: str,
        city: Optional[str],
        country: Optional[str],
        capacity: Optional[int],
        captured_at: datetime,
    ) -> None:
        stmt = pg_insert(VenueModel).values(
            venue_id=venue_id, name=name, city=city, country=country,
            capacity=capacity, captured_at=captured_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["venue_id"],
            set_={
                "name": stmt.excluded.name,
                "city": stmt.excluded.city,
                "country": stmt.excluded.country,
                "capacity": stmt.excluded.capacity,
                "captured_at": stmt.excluded.captured_at,
            },
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def find_venue(self, venue_id: str) -> Optional[dict]:
        with TransactionManager.get().read_only() as s:
            row = s.get(VenueModel, venue_id)
            return _venue_to_dict(row) if row else None

    def upsert_referee(
        self, referee_id: str, name: str, country: Optional[str], details: dict, captured_at: datetime,
    ) -> None:
        stmt = pg_insert(RefereeModel).values(
            referee_id=referee_id, name=name, country=country, details=details, captured_at=captured_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["referee_id"],
            set_={
                "name": stmt.excluded.name,
                "country": stmt.excluded.country,
                "details": stmt.excluded.details,
                "captured_at": stmt.excluded.captured_at,
            },
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def find_referee(self, referee_id: str) -> Optional[dict]:
        with TransactionManager.get().read_only() as s:
            row = s.get(RefereeModel, referee_id)
            return _referee_to_dict(row) if row else None

    def upsert_player_stats(self, match_id: UUID, stats: dict, captured_at: datetime) -> None:
        stmt = pg_insert(PlayerStatsModel).values(
            match_id=str(match_id), stats=stats, captured_at=captured_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["match_id"],
            set_={"stats": stmt.excluded.stats, "captured_at": stmt.excluded.captured_at},
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def find_player_stats(self, match_id: str) -> Optional[dict]:
        with TransactionManager.get().read_only() as s:
            row = s.get(PlayerStatsModel, match_id)
            return _player_stats_to_dict(row) if row else None

    def upsert_incidents(self, match_id: UUID, incidents: dict, captured_at: datetime) -> None:
        stmt = pg_insert(IncidentsModel).values(
            match_id=str(match_id), incidents=incidents, captured_at=captured_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["match_id"],
            set_={"incidents": stmt.excluded.incidents, "captured_at": stmt.excluded.captured_at},
        )
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def find_incidents(self, match_id: str) -> Optional[dict]:
        with TransactionManager.get().read_only() as s:
            row = s.get(IncidentsModel, match_id)
            return _incidents_to_dict(row) if row else None


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


def _team_to_dict(row: TeamModel) -> dict:
    return {
        "team_id": row.team_id,
        "name": row.name,
        "short_name": row.short_name,
        "country": row.country,
        "venue_id": row.venue_id,
    }


def _value_bet_outcome_to_dict(row: ValueBetOutcomeModel) -> dict:
    return {
        "id": row.id,
        "match_id": row.match_id,
        "market": row.market,
        "outcome": row.outcome,
        "model_probability": str(row.model_probability),
        "bookmaker": row.bookmaker,
        "best_odds": str(row.best_odds),
        "implied_probability": str(row.implied_probability),
        "edge": str(row.edge),
        "detected_at": row.detected_at.isoformat() if row.detected_at else None,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "won": row.won,
        "home_score": row.home_score,
        "away_score": row.away_score,
    }


def _venue_to_dict(row: VenueModel) -> dict:
    return {
        "venue_id": row.venue_id,
        "name": row.name,
        "city": row.city,
        "country": row.country,
        "capacity": row.capacity,
        "captured_at": row.captured_at.isoformat() if row.captured_at else None,
    }


def _referee_to_dict(row: RefereeModel) -> dict:
    return {
        "referee_id": row.referee_id,
        "name": row.name,
        "country": row.country,
        "details": row.details,
        "captured_at": row.captured_at.isoformat() if row.captured_at else None,
    }


def _player_stats_to_dict(row: PlayerStatsModel) -> dict:
    return {
        "match_id": row.match_id,
        "stats": row.stats,
        "captured_at": row.captured_at.isoformat() if row.captured_at else None,
    }


def _incidents_to_dict(row: IncidentsModel) -> dict:
    return {
        "match_id": row.match_id,
        "incidents": row.incidents,
        "captured_at": row.captured_at.isoformat() if row.captured_at else None,
    }
