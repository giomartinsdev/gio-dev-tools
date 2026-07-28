from __future__ import annotations

import uuid

from shared.transaction_manager import TransactionManager

from .models import BusDirectionModel, BusShapePointModel, BusStopModel


class StopRepository:
    def replace_directions_for_line(self, mode: str, line_code: str, directions: list[dict]) -> None:
        """`directions` is the shape returned by gtfs_stops_importer.fetch_directions_for_line:
        [{"direction_id", "headsign", "stops": [...], "shape": [...]}]."""
        with TransactionManager.get().session() as s:
            s.query(BusDirectionModel).filter(
                BusDirectionModel.mode == mode, BusDirectionModel.line_code == line_code,
            ).delete()
            s.query(BusStopModel).filter(
                BusStopModel.mode == mode, BusStopModel.line_code == line_code,
            ).delete()
            s.query(BusShapePointModel).filter(
                BusShapePointModel.mode == mode, BusShapePointModel.line_code == line_code,
            ).delete()

            for direction in directions:
                direction_id = direction["direction_id"]
                s.add(BusDirectionModel(
                    id=str(uuid.uuid4()),
                    mode=mode,
                    line_code=line_code,
                    direction_id=direction_id,
                    headsign=direction.get("headsign"),
                ))
                for stop in direction["stops"]:
                    s.add(BusStopModel(
                        id=str(uuid.uuid4()),
                        mode=mode,
                        line_code=line_code,
                        direction_id=direction_id,
                        stop_id=stop["stop_id"],
                        name=stop.get("name"),
                        latitude=stop["lat"],
                        longitude=stop["lon"],
                    ))
                for seq, point in enumerate(direction["shape"]):
                    s.add(BusShapePointModel(
                        id=str(uuid.uuid4()),
                        mode=mode,
                        line_code=line_code,
                        direction_id=direction_id,
                        sequence=seq,
                        latitude=point["lat"],
                        longitude=point["lon"],
                    ))

    def has_directions(self, mode: str, line_code: str) -> bool:
        with TransactionManager.get().read_only() as s:
            return (
                s.query(BusDirectionModel.id)
                .filter(BusDirectionModel.mode == mode, BusDirectionModel.line_code == line_code)
                .first()
                is not None
            )

    def find_directions(self, mode: str, line_code: str) -> list[dict]:
        with TransactionManager.get().read_only() as s:
            rows = (
                s.query(BusDirectionModel)
                .filter(BusDirectionModel.mode == mode, BusDirectionModel.line_code == line_code)
                .order_by(BusDirectionModel.direction_id.asc())
                .all()
            )
            return [{"direction_id": r.direction_id, "headsign": r.headsign} for r in rows]

    def find_stops(self, mode: str, line_code: str, direction_id: int | None = None) -> list[dict]:
        with TransactionManager.get().read_only() as s:
            q = s.query(BusStopModel).filter(BusStopModel.mode == mode, BusStopModel.line_code == line_code)
            if direction_id is not None:
                q = q.filter(BusStopModel.direction_id == direction_id)
            return [
                {"stop_id": r.stop_id, "name": r.name, "lat": r.latitude, "lon": r.longitude, "direction_id": r.direction_id}
                for r in q.all()
            ]

    def find_shape(self, mode: str, line_code: str, direction_id: int) -> list[dict]:
        with TransactionManager.get().read_only() as s:
            rows = (
                s.query(BusShapePointModel)
                .filter(
                    BusShapePointModel.mode == mode,
                    BusShapePointModel.line_code == line_code,
                    BusShapePointModel.direction_id == direction_id,
                )
                .order_by(BusShapePointModel.sequence.asc())
                .all()
            )
            return [{"lat": r.latitude, "lon": r.longitude} for r in rows]
