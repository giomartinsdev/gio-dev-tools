from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.transaction_manager import TransactionManager

from .models import InsightModel, MatchModel, OddsSnapshotModel


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
