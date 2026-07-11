from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

# Fixed, not configurable — matches the dashboard's DD/MM display convention
# and every recipient's locale. `reference_day_offset` is a day count, not a
# timezone choice, so one constant here is enough.
REPORT_TIMEZONE = ZoneInfo("America/Sao_Paulo")

MARKET_LABELS: dict[str, str] = {
    "1x2": "Resultado final",
    "match_result": "Resultado final",
    "over_under_15": "Mais/menos 1.5 gols",
    "over_under_25": "Mais/menos 2.5 gols",
    "over_under_35": "Mais/menos 3.5 gols",
    "over_under": "Mais/menos gols",
    "btts": "Ambos marcam (BTTS)",
}

OUTCOME_LABELS: dict[str, str] = {
    "HOME": "Casa",
    "AWAY": "Fora",
    "DRAW": "Empate",
    "YES": "Sim",
    "NO": "Não",
    "OVER": "Mais",
    "UNDER": "Menos",
}


def _kickoff_date(value_bet: dict) -> date | None:
    kickoff_at = value_bet.get("kickoff_at")
    if not kickoff_at:
        return None
    parsed = datetime.fromisoformat(kickoff_at)
    return parsed.astimezone(REPORT_TIMEZONE).date()


def filter_by_reference_day(value_bets: list[dict], reference_date: date) -> list[dict]:
    return [vb for vb in value_bets if _kickoff_date(vb) == reference_date]


def group_value_bets_by_match(value_bets: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for vb in value_bets:
        groups.setdefault(vb["match_id"], []).append(vb)
    return groups


def format_report(value_bets: list[dict], reference_date: date) -> str:
    date_label = reference_date.strftime("%d/%m/%Y")
    if not value_bets:
        return f"📊 Value bets para {date_label}\n\nNenhuma oportunidade encontrada para amanhã."

    grouped = group_value_bets_by_match(value_bets)

    lines = [f"📊 Value bets para {date_label}", ""]
    for bets in grouped.values():
        first = bets[0]
        kickoff_label = ""
        if first.get("kickoff_at"):
            kickoff_label = f" ({datetime.fromisoformat(first['kickoff_at']).astimezone(REPORT_TIMEZONE).strftime('%H:%M')})"
        home = first.get("home_team_name") or "?"
        away = first.get("away_team_name") or "?"
        lines.append(f"⚽ {home} vs {away}{kickoff_label}")
        for bet in bets:
            market = MARKET_LABELS.get(bet["market"], bet["market"])
            outcome = OUTCOME_LABELS.get(bet["outcome"], bet["outcome"])
            edge_pct = float(bet["edge"]) * 100
            lines.append(
                f"  • {market} — {outcome} | edge {edge_pct:.1f}% | "
                f"{bet['bookmaker']} @ {bet['best_odds']}"
            )
        lines.append("")

    return "\n".join(lines).rstrip()
