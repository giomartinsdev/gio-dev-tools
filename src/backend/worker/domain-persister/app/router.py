from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.application.queries.get_match import GetMatchHandler, GetMatchQuery
from src.application.queries.list_insights import ListInsightsHandler, ListInsightsQuery
from src.application.queries.list_matches import ListMatchesHandler, ListMatchesQuery
from src.application.queries.list_value_bet_outcomes import (
    ListValueBetOutcomesHandler,
    ListValueBetOutcomesQuery,
    SummarizeValueBetOutcomesHandler,
)
from src.application.queries.list_value_bets import ListValueBetsHandler, ListValueBetsQuery
from src.infrastructure.read_model_repository import ReadModelRepository

from .deps import get_read_models

router = APIRouter()


@router.get("/matches")
def list_matches(
    limit: int = 50,
    offset: int = 0,
    repo: ReadModelRepository = Depends(get_read_models),
):
    return ListMatchesHandler(repo).handle(ListMatchesQuery(limit=limit, offset=offset))


@router.get("/matches/{match_id}")
def get_match(match_id: str, repo: ReadModelRepository = Depends(get_read_models)):
    result = GetMatchHandler(repo).handle(GetMatchQuery(match_id=match_id))
    if result is None:
        raise HTTPException(status_code=404, detail="match not found")
    return result


@router.get("/insights")
def list_insights(
    match_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    repo: ReadModelRepository = Depends(get_read_models),
):
    return ListInsightsHandler(repo).handle(ListInsightsQuery(match_id=match_id, limit=limit, offset=offset))


@router.get("/value-bets")
def list_value_bets(
    match_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    repo: ReadModelRepository = Depends(get_read_models),
):
    """Currently-detected edges (model probability vs. best market price)
    above VALUE_BET_EDGE_THRESHOLD, highest edge first."""
    return ListValueBetsHandler(repo).handle(ListValueBetsQuery(match_id=match_id, limit=limit, offset=offset))


@router.get("/value-bets/outcomes")
def list_value_bet_outcomes(
    match_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    repo: ReadModelRepository = Depends(get_read_models),
):
    """Resolved value bets — whether the edge detected before a match
    finished actually won, most recently resolved first."""
    return ListValueBetOutcomesHandler(repo).handle(
        ListValueBetOutcomesQuery(match_id=match_id, limit=limit, offset=offset)
    )


@router.get("/value-bets/outcomes/summary")
def summarize_value_bet_outcomes(repo: ReadModelRepository = Depends(get_read_models)):
    """Win rate across every resolved value bet — the number that actually
    answers "does this strategy make money"."""
    return SummarizeValueBetOutcomesHandler(repo).handle()
