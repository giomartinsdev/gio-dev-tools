from __future__ import annotations

from datetime import datetime, timedelta

from shared.logger import get_logger
from src.domain.report import (
    REPORT_TIMEZONE,
    filter_by_reference_day,
    filter_outcomes_by_day,
    format_recap,
    format_report,
)

logger = get_logger(__name__)


class ReportGenerator:
    def __init__(self, value_bets_client, config_repo, recipients_repo, whatsapp_publisher):
        self._value_bets_client = value_bets_client
        self._config_repo = config_repo
        self._recipients_repo = recipients_repo
        self._whatsapp_publisher = whatsapp_publisher

    async def run(self) -> None:
        config = self._config_repo.get()
        now = datetime.now(REPORT_TIMEZONE)
        reference_date = (now + timedelta(days=config.reference_day_offset)).date()
        recap_date = (now - timedelta(days=1)).date()

        value_bets = await self._value_bets_client.fetch()
        todays_bets = filter_by_reference_day(value_bets, reference_date)

        outcomes = await self._value_bets_client.fetch_outcomes(recap_date)
        yesterdays_outcomes = filter_outcomes_by_day(outcomes, recap_date)

        text = format_recap(yesterdays_outcomes, recap_date) + "\n\n" + format_report(todays_bets, reference_date)

        recipients = self._recipients_repo.list_active()
        if not recipients:
            logger.info("value-bets-report: no active recipients, nothing sent")
            return

        for recipient in recipients:
            await self._whatsapp_publisher.publish(recipient.phone_number, text)
        logger.info(f"value-bets-report: sent to {len(recipients)} recipient(s) for {reference_date.isoformat()}")
