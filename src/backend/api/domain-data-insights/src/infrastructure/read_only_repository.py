from __future__ import annotations

from sqlalchemy import text

from shared.transaction_manager import TransactionManager

# Every table domain-persister projects into, under the bzzoiro_data schema
# it owns — this service only ever reads them (same cross-service read
# pattern asset-quotes already uses against portfolio's `assets` table), it
# never creates or migrates them.
_OVERVIEW_TABLES: list[tuple[str, str]] = [
    ("matches", "updated_at"),
    ("teams", "updated_at"),
    ("squad_members", "updated_at"),
    ("odds_snapshots", "captured_at"),
    ("odds_comparisons", "captured_at"),
    ("polymarket_snapshots", "captured_at"),
    ("insights", "generated_at"),
    ("value_bets", "detected_at"),
    ("value_bet_outcomes", "resolved_at"),
    ("lineups", "captured_at"),
    ("h2h", "captured_at"),
    ("standings", "captured_at"),
    ("venues", "captured_at"),
    ("referees", "captured_at"),
    ("player_stats", "captured_at"),
    ("incidents", "captured_at"),
]


class ReadOnlyRepository:
    """Read-only view over bzzoiro_data — populated by bzzoiro-acl and
    domain-persister, never written to by this service."""

    def get_overview(self) -> list[dict]:
        rows: list[dict] = []
        with TransactionManager.get().read_only() as s:
            for table, ts_column in _OVERVIEW_TABLES:
                result = s.execute(text(
                    f'SELECT COUNT(*) AS rows, MAX("{ts_column}") AS most_recent '
                    f'FROM bzzoiro_data."{table}"'
                )).one()
                rows.append({
                    "table": table,
                    "rows": result.rows,
                    "most_recent": result.most_recent.isoformat() if result.most_recent else None,
                })
        return rows

    def find_matches(self, limit: int = 50, offset: int = 0) -> list[dict]:
        with TransactionManager.get().read_only() as s:
            rows = s.execute(text("""
                SELECT
                    m.match_id, m.status, m.home_score, m.away_score, m.minute,
                    m.kickoff_at, m.venue,
                    ht.name AS home_team_name, at.name AS away_team_name
                FROM bzzoiro_data.matches m
                LEFT JOIN bzzoiro_data.teams ht ON ht.team_id = m.home_team_id
                LEFT JOIN bzzoiro_data.teams at ON at.team_id = m.away_team_id
                ORDER BY m.kickoff_at DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            """), {"limit": limit, "offset": offset}).mappings().all()
        return [dict(r) for r in rows]

    def find_value_bets(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Every row here already cleared VALUE_BET_EDGE_THRESHOLD — there's
        no "does this make sense" filtering left to do, `value_bets` itself
        is exactly that list. Ordered by kickoff first (soonest match's
        bets first, since those are the most time-sensitive to act on),
        then by edge within the same match, so a frontend grouping rows by
        match_id gets each match's best opportunity first without having to
        re-sort client-side."""
        with TransactionManager.get().read_only() as s:
            rows = s.execute(text("""
                SELECT
                    vb.match_id, vb.market, vb.outcome, vb.model_probability,
                    vb.bookmaker, vb.best_odds, vb.implied_probability, vb.edge,
                    vb.detected_at,
                    m.kickoff_at, m.status,
                    ht.name AS home_team_name, at.name AS away_team_name
                FROM bzzoiro_data.value_bets vb
                LEFT JOIN bzzoiro_data.matches m ON m.match_id = vb.match_id
                LEFT JOIN bzzoiro_data.teams ht ON ht.team_id = m.home_team_id
                LEFT JOIN bzzoiro_data.teams at ON at.team_id = m.away_team_id
                ORDER BY m.kickoff_at ASC NULLS LAST, vb.edge DESC
                LIMIT :limit OFFSET :offset
            """), {"limit": limit, "offset": offset}).mappings().all()
        return [dict(r) for r in rows]

    def find_value_bet_outcomes(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Most recently resolved first, so a caller paginating for "what
        resolved on day X" (value_bets_report's recap) can stop as soon as
        it sees a row older than the day it cares about."""
        with TransactionManager.get().read_only() as s:
            rows = s.execute(text("""
                SELECT
                    vbo.match_id, vbo.market, vbo.outcome, vbo.edge,
                    vbo.bookmaker, vbo.best_odds, vbo.resolved_at, vbo.won,
                    vbo.home_score, vbo.away_score,
                    ht.name AS home_team_name, at.name AS away_team_name
                FROM bzzoiro_data.value_bet_outcomes vbo
                LEFT JOIN bzzoiro_data.matches m ON m.match_id = vbo.match_id
                LEFT JOIN bzzoiro_data.teams ht ON ht.team_id = m.home_team_id
                LEFT JOIN bzzoiro_data.teams at ON at.team_id = m.away_team_id
                ORDER BY vbo.resolved_at DESC
                LIMIT :limit OFFSET :offset
            """), {"limit": limit, "offset": offset}).mappings().all()
        return [dict(r) for r in rows]

    def summarize_value_bet_outcomes(self) -> dict:
        with TransactionManager.get().read_only() as s:
            result = s.execute(text("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE won) AS won
                FROM bzzoiro_data.value_bet_outcomes
            """)).one()
        total = result.total
        won = result.won
        return {
            "total": total,
            "won": won,
            "lost": total - won,
            "win_rate": (won / total) if total else None,
        }

    def find_insights(self, limit: int = 50, offset: int = 0) -> list[dict]:
        with TransactionManager.get().read_only() as s:
            rows = s.execute(text("""
                SELECT
                    i.id, i.match_id, i.market, i.recommendation, i.confidence,
                    i.rationale, i.model, i.generated_at,
                    ht.name AS home_team_name, at.name AS away_team_name
                FROM bzzoiro_data.insights i
                LEFT JOIN bzzoiro_data.matches m ON m.match_id = i.match_id
                LEFT JOIN bzzoiro_data.teams ht ON ht.team_id = m.home_team_id
                LEFT JOIN bzzoiro_data.teams at ON at.team_id = m.away_team_id
                ORDER BY i.generated_at DESC
                LIMIT :limit OFFSET :offset
            """), {"limit": limit, "offset": offset}).mappings().all()
        return [dict(r) for r in rows]
