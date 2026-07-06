from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from shared.logger import get_logger

from ..infrastructure.read_model_repository import ReadModelRepository

logger = get_logger(__name__)


class ValueBetOutcomeResolver:
    """Answers the question the "current state" `value_bets` table can't:
    did a detected edge actually pay off? Runs when MatchFinished lands —
    whatever is still open in `value_bets` for that match at that moment
    gets archived into `value_bet_outcomes` with the real result, then
    cleared from `value_bets` (the match is over either way, so it's no
    longer an actionable opportunity).

    This only captures bets still open right at kick-off/finish — a value
    bet that existed earlier and closed before the match (edge dropped, or
    lineup confidence recovered) was already deleted by ValueBetDetector
    and never makes it into this history. That's an intentional simplicity
    trade-off for v1: it answers "did my final picks win", not "did every
    edge that ever existed win", which would need ValueBetDetector to never
    delete and this resolver to reconcile every past snapshot instead.
    """

    def __init__(self, read_models: ReadModelRepository):
        self._read_models = read_models

    def resolve_match(self, match_id: object, home_score: int, away_score: int) -> None:
        match_id_str = str(match_id)
        open_bets = self._read_models.find_value_bets(match_id=match_id_str)
        if not open_bets:
            return

        resolved_at = datetime.now(timezone.utc)
        for bet in open_bets:
            won = self._did_outcome_hit(bet["market"], bet["outcome"], home_score, away_score)
            self._read_models.insert_value_bet_outcome(
                match_id=match_id,
                market=bet["market"],
                outcome=bet["outcome"],
                model_probability=Decimal(bet["model_probability"]),
                bookmaker=bet["bookmaker"],
                best_odds=Decimal(bet["best_odds"]),
                implied_probability=Decimal(bet["implied_probability"]),
                edge=Decimal(bet["edge"]),
                detected_at=datetime.fromisoformat(bet["detected_at"]),
                resolved_at=resolved_at,
                won=won,
                home_score=home_score,
                away_score=away_score,
            )
            self._read_models.delete_value_bet(match_id, bet["market"], bet["outcome"])
            logger.info(
                f"value bet resolved: match={match_id_str} market={bet['market']} "
                f"outcome={bet['outcome']} won={won} score={home_score}-{away_score}"
            )

    @staticmethod
    def _did_outcome_hit(market: str, outcome: str, home_score: int, away_score: int) -> bool:
        total_goals = home_score + away_score

        if market == "1x2":
            if outcome == "HOME":
                return home_score > away_score
            if outcome == "DRAW":
                return home_score == away_score
            if outcome == "AWAY":
                return away_score > home_score
            return False

        if market.startswith("over_under_"):
            # over_under_15 -> line 1.5, over_under_25 -> 2.5, over_under_35 -> 3.5
            line = int(market.rsplit("_", 1)[-1]) / 10
            if outcome == "over":
                return total_goals > line
            if outcome == "under":
                return total_goals < line
            return False

        if market == "btts":
            both_scored = home_score > 0 and away_score > 0
            if outcome == "yes":
                return both_scored
            if outcome == "no":
                return not both_scored
            return False

        logger.warning(f"unknown market {market!r} for outcome resolution — treating as not hit")
        return False
