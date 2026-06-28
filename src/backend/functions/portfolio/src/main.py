import threading
from decimal import Decimal

from shared.logger import get_logger
from shared.request import Request
from shared.response import Response
from shared.secret_manager import SecretManager
from shared.transaction_manager import TransactionConfig, TransactionManager
from sqlalchemy import inspect, text

from .application.commands.create_asset import CreateAssetCommand, CreateAssetHandler
from .application.commands.update_asset import UpdateAssetCommand, UpdateAssetHandler
from .application.commands.delete_asset import DeleteAssetCommand, DeleteAssetHandler
from .domain.events import AssetCreated, AssetUpdated, AssetDeleted
from .infrastructure.event_bus import get_event_bus
from .infrastructure.models import Base
from .infrastructure.repository import PostgresAssetRepository

logger = get_logger(__name__)

_repo = None
_bus = None
_init_done = threading.Event()
_init_error: Exception | None = None


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
        return
    if "ticker" not in cols:
        logger.info("migration: adding ticker column to assets")
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE assets ADD COLUMN ticker VARCHAR"))


def _init():
    global _repo, _bus, _init_error
    if _repo is not None:
        _init_done.set()
        return
    try:
        sm = SecretManager()
        TransactionManager.configure(TransactionConfig(url=sm.get_secret("DATABASE_URL")))
        Base.metadata.create_all(TransactionManager.get().engine)
        _migrate()
        _repo = PostgresAssetRepository()
        _bus = get_event_bus()
        _bus.subscribe(AssetCreated, lambda e: logger.info(f"AssetCreated id={e.asset_id} type={e.type} qty={e.quantity} price={e.purchase_price}"))
        _bus.subscribe(AssetUpdated, lambda e: logger.info(f"AssetUpdated old={e.old_asset_id} new={e.new_asset_id} qty={e.quantity} price={e.purchase_price}"))
        _bus.subscribe(AssetDeleted, lambda e: logger.info(f"AssetDeleted id={e.asset_id}"))
    except Exception as e:
        _init_error = e
        logger.error(f"init failed: {e}", exc_info=True)
    finally:
        _init_done.set()


threading.Thread(target=_init, daemon=True).start()


def _fetch_quotes(tickers: list[str]) -> dict[str, dict]:
    if not tickers:
        return {}
    try:
        with TransactionManager.get().read_only() as s:
            rows = s.execute(
                text("""
                    SELECT DISTINCT ON (ticker)
                        ticker, price, daily_change, daily_change_pct,
                        last_dividend, last_dividend_date, recorded_at
                    FROM quote_events
                    WHERE ticker = ANY(:tickers)
                    ORDER BY ticker, recorded_at DESC
                """),
                {"tickers": tickers},
            ).fetchall()
        return {r.ticker: dict(r._mapping) for r in rows}
    except Exception as e:
        logger.warning(f"failed to fetch quotes: {e}")
        return {}


def _build_quote(asset, raw: dict) -> dict | None:
    if not raw:
        return None
    price = Decimal(str(raw["price"])) if raw.get("price") else None
    if price is None:
        return None
    current_value = asset.quantity * price
    gain_loss = current_value - asset.total_value
    gain_loss_pct = (gain_loss / asset.total_value * 100) if asset.total_value else Decimal(0)
    return {
        "price": str(price),
        "daily_change": str(raw["daily_change"]) if raw.get("daily_change") is not None else None,
        "daily_change_pct": str(raw["daily_change_pct"]) if raw.get("daily_change_pct") is not None else None,
        "current_value": str(current_value.quantize(Decimal("0.01"))),
        "gain_loss": str(gain_loss.quantize(Decimal("0.01"))),
        "gain_loss_pct": str(gain_loss_pct.quantize(Decimal("0.01"))),
        "last_dividend": str(raw["last_dividend"]) if raw.get("last_dividend") is not None else None,
        "last_dividend_date": raw["last_dividend_date"].isoformat() if raw.get("last_dividend_date") else None,
        "recorded_at": raw["recorded_at"].isoformat() if raw.get("recorded_at") else None,
    }


def main(request: Request) -> Response:
    _init_done.wait()
    if _init_error is not None:
        return Response(body={"error": "service unavailable"}, status_code=503)
    try:
        if request.method == "GET":
            assets = _repo.find_all()
            tickers = [a.ticker for a in assets if a.ticker]
            quotes = _fetch_quotes(tickers)
            return Response(
                body=[a.to_dict(quote=_build_quote(a, quotes.get(a.ticker, {}))) for a in assets],
                status_code=200,
            )

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
        ticker=str(request.body.get("ticker", "")),
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
        ticker=str(request.body.get("ticker", "")),
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
