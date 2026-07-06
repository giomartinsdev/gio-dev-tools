from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.application.queries.get_match import GetMatchHandler, GetMatchQuery
from src.application.queries.list_insights import ListInsightsHandler, ListInsightsQuery
from src.application.queries.list_matches import ListMatchesHandler, ListMatchesQuery
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
