from shared.logger import get_logger
from shared.request import Request
from shared.response import Response

from .application.commands.create_asset import CreateAssetCommand, CreateAssetHandler
from .application.commands.update_asset import UpdateAssetCommand, UpdateAssetHandler
from .application.commands.delete_asset import DeleteAssetCommand, DeleteAssetHandler
from .domain.events import AssetCreated, AssetUpdated, AssetDeleted
from .infrastructure.event_bus import get_event_bus
from .infrastructure.repository import PostgresAssetRepository, migrate

logger = get_logger(__name__)

migrate()

_repo = PostgresAssetRepository()
_bus = get_event_bus()
_bus.subscribe(AssetCreated, lambda e: logger.info(f"AssetCreated id={e.asset_id} type={e.type} amount={e.amount}"))
_bus.subscribe(AssetUpdated, lambda e: logger.info(f"AssetUpdated id={e.asset_id} name={e.name} amount={e.amount}"))
_bus.subscribe(AssetDeleted, lambda e: logger.info(f"AssetDeleted id={e.asset_id}"))


def main(request: Request) -> Response:
    try:
        if request.method == "GET":
            return Response(body=[a.to_dict() for a in _repo.find_all()], status_code=200)

        if request.method == "POST":
            return _create(request)

        if request.method == "PATCH":
            return _update(request)

        if request.method == "DELETE":
            return _delete(request)

        return Response(body={"error": "method not allowed"}, status_code=405)

    except ValueError as e:
        return Response(body={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"unhandled error: {e}", exc_info=True)
        return Response(body={"error": "internal server error"}, status_code=500)


def _create(request: Request) -> Response:
    asset = CreateAssetHandler(_repo, _bus).handle(CreateAssetCommand(
        name=str(request.body.get("name", "")),
        type=str(request.body.get("type", "")),
        institution=str(request.body.get("institution", "")),
        amount=str(request.body.get("amount", "")),
    ))
    return Response(body=asset.to_dict(), status_code=201)


def _update(request: Request) -> Response:
    asset = UpdateAssetHandler(_repo, _bus).handle(UpdateAssetCommand(
        asset_id=str(request.body.get("id", "")),
        name=str(request.body.get("name", "")),
        type=str(request.body.get("type", "")),
        institution=str(request.body.get("institution", "")),
        amount=str(request.body.get("amount", "")),
    ))
    if asset is None:
        return Response(body={"error": "asset not found"}, status_code=404)
    return Response(body=asset.to_dict(), status_code=200)


def _delete(request: Request) -> Response:
    deleted = DeleteAssetHandler(_repo, _bus).handle(
        DeleteAssetCommand(asset_id=str(request.body.get("id", "")))
    )
    if not deleted:
        return Response(body={"error": "asset not found"}, status_code=404)
    return Response(body={"deleted": True}, status_code=200)
