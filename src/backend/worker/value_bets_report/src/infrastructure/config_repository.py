from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from shared.transaction_manager import TransactionManager

from .models import ReportConfigModel


@dataclass
class ReportConfig:
    send_time: str
    reference_day_offset: int
    enabled: bool
    realtime_alerts_enabled: bool
    realtime_edge_threshold: Decimal


class ConfigRepository:
    def get(self) -> ReportConfig:
        with TransactionManager.get().read_only() as s:
            row = s.get(ReportConfigModel, 1)
            return ReportConfig(
                send_time=row.send_time,
                reference_day_offset=row.reference_day_offset,
                enabled=row.enabled,
                realtime_alerts_enabled=row.realtime_alerts_enabled,
                realtime_edge_threshold=row.realtime_edge_threshold,
            )

    def update(
        self,
        send_time: str,
        reference_day_offset: int,
        enabled: bool,
        realtime_alerts_enabled: bool,
        realtime_edge_threshold: Decimal,
    ) -> ReportConfig:
        with TransactionManager.get().session() as s:
            row = s.get(ReportConfigModel, 1)
            row.send_time = send_time
            row.reference_day_offset = reference_day_offset
            row.enabled = enabled
            row.realtime_alerts_enabled = realtime_alerts_enabled
            row.realtime_edge_threshold = realtime_edge_threshold
        return ReportConfig(
            send_time=send_time,
            reference_day_offset=reference_day_offset,
            enabled=enabled,
            realtime_alerts_enabled=realtime_alerts_enabled,
            realtime_edge_threshold=realtime_edge_threshold,
        )
