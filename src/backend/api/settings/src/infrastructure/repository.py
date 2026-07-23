from typing import Optional

from shared.transaction_manager import TransactionManager
from shared.timezone_handler import TimezoneAware

from ..domain.service import Service, ServiceCategory, ServiceStatus
from ..domain.repository import ServiceRepository
from .models import ServiceModel

_SP = TimezoneAware("America/Sao_Paulo")


class PostgresServiceRepository(ServiceRepository):
    def save(self, service: Service) -> None:
        with TransactionManager.get().session() as s:
            s.add(ServiceModel(
                id=service.id,
                name=service.name,
                category=service.category.value,
                status=service.status.value,
                secret_ref=service.secret_ref,
                notes=service.notes,
            ))

    def update(self, service: Service) -> None:
        with TransactionManager.get().session() as s:
            row = s.get(ServiceModel, service.id)
            if row is None or row.deleted_at is not None:
                return
            row.name = service.name
            row.category = service.category.value
            row.status = service.status.value
            row.secret_ref = service.secret_ref
            row.notes = service.notes

    def delete(self, service_id: str) -> bool:
        with TransactionManager.get().session() as s:
            row = s.get(ServiceModel, service_id)
            if row is None or row.deleted_at is not None:
                return False
            row.deleted_at = _SP.now
            return True

    def find_all(self) -> list[Service]:
        with TransactionManager.get().read_only() as s:
            rows = (
                s.query(ServiceModel)
                .filter(ServiceModel.deleted_at.is_(None))
                .order_by(ServiceModel.created_at.asc())
                .all()
            )
            return [_to_domain(r) for r in rows]

    def find_by_id(self, service_id: str) -> Optional[Service]:
        with TransactionManager.get().read_only() as s:
            row = s.get(ServiceModel, service_id)
            if row is None or row.deleted_at is not None:
                return None
            return _to_domain(row)


def _to_domain(row: ServiceModel) -> Service:
    return Service(
        id=row.id,
        name=row.name,
        category=ServiceCategory(row.category),
        status=ServiceStatus(row.status),
        secret_ref=row.secret_ref,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
