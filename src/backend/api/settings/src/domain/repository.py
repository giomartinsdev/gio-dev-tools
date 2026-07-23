from abc import ABC, abstractmethod
from typing import Optional

from .service import Service


class ServiceRepository(ABC):
    @abstractmethod
    def save(self, service: Service) -> None: ...

    @abstractmethod
    def update(self, service: Service) -> None: ...

    @abstractmethod
    def delete(self, service_id: str) -> bool: ...

    @abstractmethod
    def find_all(self) -> list[Service]: ...

    @abstractmethod
    def find_by_id(self, service_id: str) -> Optional[Service]: ...
