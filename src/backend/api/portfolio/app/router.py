from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from shared.logger import get_logger
from shared.transaction_manager import TransactionManager
from src.application.commands.create_asset import CreateAssetCommand, CreateAssetHandler
from src.application.commands.update_asset import UpdateAssetCommand, UpdateAssetHandler
from src.application.commands.delete_asset import DeleteAssetCommand, DeleteAssetHandler
from src.infrastructure.repository import PostgresAssetRepository
from src.infrastructure.event_bus import EventBus

from .deps import get_repo, get_bus
from .schemas import CreateAssetRequest, UpdateAssetRequest

logger = get_logger(__name__)

router = APIRouter()


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


@router.get("/assets")
def list_assets(repo: PostgresAssetRepository = Depends(get_repo)):
    assets = repo.find_all()
    tickers = [a.ticker for a in assets if a.ticker]
    quotes = _fetch_quotes(tickers)
    return [a.to_dict(quote=_build_quote(a, quotes.get(a.ticker, {}))) for a in assets]


@router.post("/assets", status_code=201)
def create_asset(
    body: CreateAssetRequest,
    repo: PostgresAssetRepository = Depends(get_repo),
    bus: EventBus = Depends(get_bus),
):
    try:
        asset = CreateAssetHandler(repo, bus).handle(CreateAssetCommand(
            name=body.name,
            type=body.type,
            institution=body.institution,
            quantity=body.quantity,
            purchase_price=body.purchase_price,
            ticker=body.ticker,
        ))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return asset.to_dict()


@router.patch("/assets/{asset_id}", status_code=200)
def update_asset(
    asset_id: str,
    body: UpdateAssetRequest,
    repo: PostgresAssetRepository = Depends(get_repo),
    bus: EventBus = Depends(get_bus),
):
    try:
        asset = UpdateAssetHandler(repo, bus).handle(UpdateAssetCommand(
            asset_id=asset_id,
            name=body.name,
            type=body.type,
            institution=body.institution,
            quantity=body.quantity,
            purchase_price=body.purchase_price,
            ticker=body.ticker,
        ))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return asset.to_dict()


@router.delete("/assets/{asset_id}", status_code=200)
def delete_asset(
    asset_id: str,
    repo: PostgresAssetRepository = Depends(get_repo),
    bus: EventBus = Depends(get_bus),
):
    deleted = DeleteAssetHandler(repo, bus).handle(DeleteAssetCommand(asset_id=asset_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="asset not found")
    return {"deleted": True}
