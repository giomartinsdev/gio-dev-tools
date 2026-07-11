from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from shared.logger import get_logger
from src.domain.report import REPORT_TIMEZONE

logger = get_logger(__name__)

CONFIG_POLL_INTERVAL = 60  # seconds between config re-reads while disabled/idle


def compute_next_fire(now: datetime, send_time: str) -> datetime:
    """`send_time` is "HH:MM". Returns the next occurrence at/after `now` —
    today if that time hasn't passed yet, tomorrow otherwise."""
    hour, minute = (int(p) for p in send_time.split(":"))
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


class DailyScheduler:
    """Re-reads config every cycle so a `PUT /config` change (time or
    enabled) takes effect without restarting the worker."""

    def __init__(self, config_repo, trigger_publisher):
        self._config_repo = config_repo
        self._trigger_publisher = trigger_publisher

    async def run(self) -> None:
        while True:
            config = self._config_repo.get()
            if not config.enabled:
                await asyncio.sleep(CONFIG_POLL_INTERVAL)
                continue

            now = datetime.now(REPORT_TIMEZONE)
            next_fire = compute_next_fire(now, config.send_time)
            wait_seconds = (next_fire - now).total_seconds()
            logger.info(f"next value-bets-report fire at {next_fire.isoformat()}")
            await asyncio.sleep(min(wait_seconds, CONFIG_POLL_INTERVAL))

            now = datetime.now(REPORT_TIMEZONE)
            if now >= next_fire:
                await self._trigger_publisher.publish(reason="scheduled")
