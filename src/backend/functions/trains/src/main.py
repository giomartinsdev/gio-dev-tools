import httpx

from shared.logger import get_logger
from shared.request import Request
from shared.response import Response

from .application.queries.get_live_trip import GetLiveTripHandler, GetLiveTripQuery
from .application.queries.list_lines import ListLinesHandler, ListLinesQuery
from .application.queries.list_stations import ListStationsHandler, ListStationsQuery
from .domain.events import LinesQueried, LiveTripQueried, StationsQueried
from .infrastructure.event_bus import get_event_bus
from .infrastructure.trens_rj_client import TrensRjClient
from .infrastructure.trens_rj_repository import (
    TrensRjLineRepository,
    TrensRjStationRepository,
    TrensRjTripRepository,
)

logger = get_logger(__name__)

_client = TrensRjClient()
_station_repo = TrensRjStationRepository(_client)
_line_repo = TrensRjLineRepository(_client)
_trip_repo = TrensRjTripRepository(_client)

_bus = get_event_bus()
_bus.subscribe(StationsQueried, lambda e: logger.info(f"StationsQueried count={e.count}"))
_bus.subscribe(LinesQueried, lambda e: logger.info(f"LinesQueried count={e.count}"))
_bus.subscribe(LiveTripQueried, lambda e: logger.info(f"LiveTripQueried station={e.station_id} line={e.line_id} dir={e.direction}"))


def main(request: Request) -> Response:
    try:
        path = request.path.rstrip("/") or "/"

        if request.method == "GET" and path.endswith("/live"):
            return _live(request)

        if request.method == "GET" and path.endswith("/lines"):
            return _lines(request)

        if request.method == "GET":
            return _stations(request)

        return Response(body={"error": "method not allowed"}, status_code=405)

    except ValueError as e:
        return Response(body={"error": str(e)}, status_code=400)
    except httpx.HTTPStatusError as e:
        return Response(body={"error": str(e)}, status_code=e.response.status_code)
    except Exception as e:
        logger.error(f"unhandled error: {e}", exc_info=True)
        return Response(body={"error": "internal server error"}, status_code=500)


def _stations(request: Request) -> Response:
    stations = ListStationsHandler(_station_repo).handle(ListStationsQuery())
    _bus.publish(StationsQueried(count=len(stations)))
    return Response(body=[s.to_dict() for s in stations], status_code=200)


def _lines(request: Request) -> Response:
    lines = ListLinesHandler(_line_repo).handle(ListLinesQuery())
    _bus.publish(LinesQueried(count=len(lines)))
    return Response(body=[l.to_dict() for l in lines], status_code=200)


def _live(request: Request) -> Response:
    station_id = request.query.get("stationId", "")
    line_id = request.query.get("lineId", "")
    direction = request.query.get("direction", "")

    if not station_id or not line_id or not direction:
        return Response(
            body={"error": "stationId, lineId and direction are required"},
            status_code=400,
        )

    trip = GetLiveTripHandler(_trip_repo).handle(
        GetLiveTripQuery(station_id=station_id, line_id=line_id, direction=direction)
    )
    _bus.publish(LiveTripQueried(station_id=station_id, line_id=line_id, direction=direction))
    return Response(body=trip.to_dict(), status_code=200)
