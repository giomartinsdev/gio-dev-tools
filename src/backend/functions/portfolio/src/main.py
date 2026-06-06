import os

from shared.logger import get_logger
from shared.request import Request
from shared.response import Response
from shared.transaction_manager import TransactionConfig, TransactionManager
from sqlalchemy import inspect

from .application.commands.create_asset import CreateAssetCommand, CreateAssetHandler
from .application.commands.update_asset import UpdateAssetCommand, UpdateAssetHandler
from .application.commands.delete_asset import DeleteAssetCommand, DeleteAssetHandler
from .domain.events import AssetCreated, AssetUpdated, AssetDeleted
from .infrastructure.event_bus import get_event_bus
from .infrastructure.models import Base
from .infrastructure.repository import PostgresAssetRepository

logger = get_logger(__name__)


def _migrate() -> None:
    engine = TransactionManager.get().engine
    insp = inspect(engine)
    if "assets" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("assets")}
    if "amount" in cols:
        logger.info("migration: old schema (amount) detected — recreating assets table")
        Base.metadata.drop_all(engine, tables=[Base.metadata.tables["assets"]])
        Base.metadata.create_all(engine, tables=[Base.metadata.tables["assets"]])


TransactionManager.configure(TransactionConfig(url=os.environ["DATABASE_URL"]))
Base.metadata.create_all(TransactionManager.get().engine)
_migrate()


_repo = PostgresAssetRepository()
_bus = get_event_bus()
_bus.subscribe(AssetCreated, lambda e: logger.info(f"AssetCreated id={e.asset_id} type={e.type} qty={e.quantity} price={e.purchase_price}"))
_bus.subscribe(AssetUpdated, lambda e: logger.info(f"AssetUpdated old={e.old_asset_id} new={e.new_asset_id} qty={e.quantity} price={e.purchase_price}"))
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
        quantity=str(request.body.get("quantity", "")),
        purchase_price=str(request.body.get("purchase_price", "")),
    ))
    return Response(body=asset.to_dict(), status_code=201)


def _update(request: Request) -> Response:
    asset = UpdateAssetHandler(_repo, _bus).handle(UpdateAssetCommand(
        asset_id=str(request.body.get("id", "")),
        name=str(request.body.get("name", "")),
        type=str(request.body.get("type", "")),
        institution=str(request.body.get("institution", "")),
        quantity=str(request.body.get("quantity", "")),
        purchase_price=str(request.body.get("purchase_price", "")),
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
