from __future__ import annotations

from dataclasses import dataclass

from shared.transaction_manager import TransactionManager

from .models import ReportConfigModel


@dataclass
class ReportConfig:
    send_time: str
    reference_day_offset: int
    enabled: bool


class ConfigRepository:
    def get(self) -> ReportConfig:
        with TransactionManager.get().read_only() as s:
            row = s.get(ReportConfigModel, 1)
            return ReportConfig(
                send_time=row.send_time,
                reference_day_offset=row.reference_day_offset,
                enabled=row.enabled,
            )

    def update(self, send_time: str, reference_day_offset: int, enabled: bool) -> ReportConfig:
        with TransactionManager.get().session() as s:
            row = s.get(ReportConfigModel, 1)
            row.send_time = send_time
            row.reference_day_offset = reference_day_offset
            row.enabled = enabled
        return ReportConfig(send_time=send_time, reference_day_offset=reference_day_offset, enabled=enabled)
