from __future__ import annotations

from fastapi import APIRouter, Depends

from src.infrastructure.read_only_repository import ReadOnlyRepository

from .deps import get_repo

router = APIRouter()


@router.get("/overview")
def get_overview(repo: ReadOnlyRepository = Depends(get_repo)):
    """Row count + most recent timestamp per bzzoiro_data table — the
    at-a-glance "is data actually arriving" view."""
    return repo.get_overview()


@router.get("/matches")
def list_matches(
    limit: int = 50,
    offset: int = 0,
    repo: ReadOnlyRepository = Depends(get_repo),
):
    return repo.find_matches(limit=limit, offset=offset)


@router.get("/value-bets")
def list_value_bets(
    limit: int = 50,
    offset: int = 0,
    repo: ReadOnlyRepository = Depends(get_repo),
):
    return repo.find_value_bets(limit=limit, offset=offset)


@router.get("/value-bets/outcomes/summary")
def summarize_value_bet_outcomes(repo: ReadOnlyRepository = Depends(get_repo)):
    return repo.summarize_value_bet_outcomes()


@router.get("/insights")
def list_insights(
    limit: int = 50,
    offset: int = 0,
    repo: ReadOnlyRepository = Depends(get_repo),
):
    return repo.find_insights(limit=limit, offset=offset)
