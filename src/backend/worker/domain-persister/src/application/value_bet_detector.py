from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from shared.logger import get_logger

from ..infrastructure.read_model_repository import ReadModelRepository

logger = get_logger(__name__)

# (path into InsightModel.feature_snapshot, odds market key, odds outcome key)
# feature_snapshot mirrors bzzoiro's PredictionV2MarketsSchema: match_result,
# expected_goals, over_under, btts, score. Odds markets/outcomes mirror
# OddsItemV2Schema's enums (see bzzoiro-acl's translator/bzzoiro_client).
_MARKET_MAP: list[tuple[tuple[str, str], str, str]] = [
    (("match_result", "prob_home"), "1x2", "HOME"),
    (("match_result", "prob_draw"), "1x2", "DRAW"),
    (("match_result", "prob_away"), "1x2", "AWAY"),
    (("over_under", "prob_over_15"), "over_under_15", "over"),
    (("over_under", "prob_over_25"), "over_under_25", "over"),
    (("over_under", "prob_over_35"), "over_under_35", "over"),
    (("btts", "prob_yes"), "btts", "yes"),
]


class ValueBetDetector:
    """Correlates bzzoiro's own model probability (InsightGenerated) against
    the best market price (OddsComparisonCaptured) for the same match.
    `edge = model_probability - implied_probability`; above `edge_threshold`
    it's upserted as a value bet, otherwise any previously-recorded value
    bet for that (match, market, outcome) is removed — this tracks current
    opportunities, not a history of every recomputation.

    Runs after any of the four inputs lands (a new insight, odds
    comparison/best, or lineup) for a match; a no-op if insight+odds aren't
    both there yet.

    Lineup confidence acts as a trust filter, not another data source: if
    bzzoiro's own AI-predicted lineup for either side is below
    `lineup_confidence_threshold`, an edge is suppressed rather than acted
    on — a low-confidence predicted XI means the real team news might not
    be priced into the model or the odds yet, so an apparent mispricing
    could just be uncertainty about who's actually playing, not a real
    edge. No lineup data yet (not polled, or not available for this match)
    doesn't block detection — only a lineup that HAS been captured with
    low confidence does.
    """

    def __init__(
        self,
        read_models: ReadModelRepository,
        edge_threshold: Decimal,
        lineup_confidence_threshold: Decimal = Decimal("0.6"),
    ):
        self._read_models = read_models
        self._edge_threshold = edge_threshold
        self._lineup_confidence_threshold = lineup_confidence_threshold

    def evaluate(self, match_id: object) -> None:
        match_id_str = str(match_id)
        insight = self._read_models.find_latest_insight(match_id_str)
        comparison = self._read_models.find_odds_comparison(match_id_str)
        if insight is None or comparison is None:
            return

        feature_snapshot = insight.get("feature_snapshot") or {}
        markets = comparison.get("markets") or {}
        lineup_confidence = self._extract_lineup_confidence(self._read_models.find_lineups(match_id_str))

        for (group_key, prob_key), odds_market, odds_outcome in _MARKET_MAP:
            model_prob = self._extract_probability(feature_snapshot, group_key, prob_key)
            if model_prob is None:
                continue

            outcome_data = (markets.get(odds_market) or {}).get(odds_outcome)
            best_odds = self._extract_best_odds(outcome_data)
            best_bookmaker = (outcome_data or {}).get("best_bookmaker_slug")
            if best_odds is None or not best_bookmaker:
                self._read_models.delete_value_bet(match_id, odds_market, odds_outcome)
                continue

            implied_probability = Decimal("1") / best_odds
            edge = model_prob - implied_probability

            if edge > self._edge_threshold and self._lineup_confidence_ok(lineup_confidence):
                self._read_models.upsert_value_bet(
                    match_id=match_id,
                    market=odds_market,
                    outcome=odds_outcome,
                    model_probability=model_prob,
                    bookmaker=best_bookmaker,
                    best_odds=best_odds,
                    implied_probability=implied_probability,
                    edge=edge,
                    detected_at=datetime.now(timezone.utc),
                )
                logger.info(
                    f"value bet: match={match_id_str} market={odds_market} outcome={odds_outcome} "
                    f"edge={edge:.4f} bookmaker={best_bookmaker} odds={best_odds}"
                )
            else:
                if edge > self._edge_threshold:
                    logger.info(
                        f"value bet suppressed: match={match_id_str} market={odds_market} "
                        f"outcome={odds_outcome} edge={edge:.4f} but lineup confidence "
                        f"{lineup_confidence} < {self._lineup_confidence_threshold} — "
                        f"team news may not be priced in yet"
                    )
                self._read_models.delete_value_bet(match_id, odds_market, odds_outcome)

    def _lineup_confidence_ok(self, lineup_confidence: Optional[Decimal]) -> bool:
        if lineup_confidence is None:
            return True
        return lineup_confidence >= self._lineup_confidence_threshold

    @staticmethod
    def _extract_lineup_confidence(lineups_row: Optional[dict]) -> Optional[Decimal]:
        if not lineups_row:
            return None
        lineups = lineups_row.get("lineups") or {}
        values = []
        for side in ("home", "away"):
            confidence = (lineups.get(side) or {}).get("confidence")
            if confidence is not None:
                try:
                    values.append(Decimal(str(confidence)))
                except Exception:
                    continue
        return min(values) if values else None

    @staticmethod
    def _extract_probability(feature_snapshot: dict, group_key: str, prob_key: str) -> Optional[Decimal]:
        """bzzoiro's `markets` block reports every `prob_*` field on a
        0-100 percentage scale (confirmed live: `match_result.prob_home:
        55.5`, `over_under.prob_over_25: 65.2`, summing to ~100 across
        match_result's three outcomes) — not the 0-1 fraction this used to
        assume. Feeding a raw 55.5 into `edge = model_probability -
        implied_probability` produced nonsense edges over 30 (3000+
        percentage points) that overflowed `value_bets.model_probability`'s
        `Numeric(6,5)` column and poisoned the message. Dividing by 100
        here keeps every other calculation (edge, implied_probability, the
        threshold comparison) working in the same 0-1 fraction space as
        `implied_probability = 1 / best_odds`."""
        value = (feature_snapshot.get(group_key) or {}).get(prob_key)
        if value is None:
            return None
        try:
            return Decimal(str(value)) / Decimal("100")
        except Exception:
            return None

    @staticmethod
    def _extract_best_odds(outcome_data: Optional[dict]) -> Optional[Decimal]:
        if not outcome_data:
            return None
        value = outcome_data.get("best_odds")
        if not value:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None
