from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.transaction_manager import TransactionManager

from .models import BusPositionModel


class PositionRepository:
    def insert(
        self,
        mode: str,
        line_code: str,
        vehicle_id: str,
        latitude: float,
        longitude: float,
        speed_kmh: float,
        captured_at: datetime,
        color_hex: Optional[str] = None,
    ) -> None:
        """Idempotent insert: both the SPPO and BRT feeds re-send the same
        ping across consecutive polls, so (vehicle_id, captured_at) is the
        natural dedup key — a repeat is silently dropped rather than
        duplicated."""
        stmt = pg_insert(BusPositionModel).values(
            id=str(uuid.uuid4()),
            mode=mode,
            line_code=line_code,
            vehicle_id=vehicle_id,
            latitude=latitude,
            longitude=longitude,
            speed_kmh=speed_kmh,
            color_hex=color_hex,
            captured_at=captured_at,
        ).on_conflict_do_nothing(constraint="uq_bus_position_vehicle_captured")
        with TransactionManager.get().session() as s:
            s.execute(stmt)

    def find_latest(self, mode: str, line_code: str) -> list[dict]:
        """Most recent position per vehicle for the given mode+line."""
        with TransactionManager.get().read_only() as s:
            rows = (
                s.query(BusPositionModel)
                .filter(BusPositionModel.mode == mode, BusPositionModel.line_code == line_code)
                .order_by(BusPositionModel.captured_at.desc())
                .limit(500)
                .all()
            )
            latest_by_vehicle: dict[str, BusPositionModel] = {}
            for row in rows:
                if row.vehicle_id not in latest_by_vehicle:
                    latest_by_vehicle[row.vehicle_id] = row
            return [_to_dict(r) for r in latest_by_vehicle.values()]

    def find_history(self, mode: str, line_code: str, limit: int = 50, offset: int = 0) -> list[dict]:
        with TransactionManager.get().read_only() as s:
            rows = (
                s.query(BusPositionModel)
                .filter(BusPositionModel.mode == mode, BusPositionModel.line_code == line_code)
                .order_by(BusPositionModel.captured_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            return [_to_dict(r) for r in rows]


def _to_dict(row: BusPositionModel) -> dict:
    return {
        "mode": row.mode,
        "line_code": row.line_code,
        "vehicle_id": row.vehicle_id,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "speed_kmh": row.speed_kmh,
        "color_hex": row.color_hex,
        "captured_at": row.captured_at.isoformat() if row.captured_at else None,
    }
