from __future__ import annotations

import asyncio
from decimal import Decimal

from shared.logger import get_logger
from src.domain.report import format_realtime_alert

logger = get_logger(__name__)

POLL_INTERVAL_SECONDS = 300


class RealtimeAlertChecker:
    """Polls current value bets for ones crossing `realtime_edge_threshold`
    and not yet alerted (dedup via RealtimeAlertLogRepository — `value_bets`
    is a current-state table, so the same open opportunity would otherwise
    re-trigger on every poll)."""

    def __init__(self, value_bets_client, config_repo, recipients_repo, alert_log_repo, whatsapp_publisher):
        self._value_bets_client = value_bets_client
        self._config_repo = config_repo
        self._recipients_repo = recipients_repo
        self._alert_log_repo = alert_log_repo
        self._whatsapp_publisher = whatsapp_publisher

    async def check_once(self) -> None:
        config = self._config_repo.get()
        if not config.realtime_alerts_enabled:
            return

        recipients = self._recipients_repo.list_realtime_subscribers()
        if not recipients:
            return

        value_bets = await self._value_bets_client.fetch()
        threshold = Decimal(config.realtime_edge_threshold)

        for vb in value_bets:
            if Decimal(vb["edge"]) < threshold:
                continue
            if self._alert_log_repo.is_alerted(vb["match_id"], vb["market"], vb["outcome"]):
                continue

            text = format_realtime_alert(vb)
            for recipient in recipients:
                await self._whatsapp_publisher.publish(recipient.phone_number, text)
            self._alert_log_repo.mark_alerted(vb["match_id"], vb["market"], vb["outcome"])
            logger.info(f"value-bets-report: realtime alert sent for {vb['match_id']}/{vb['market']}/{vb['outcome']}")

    async def run(self) -> None:
        while True:
            try:
                await self.check_once()
            except Exception as exc:
                logger.error(f"realtime alert check failed: {exc}", exc_info=True)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
