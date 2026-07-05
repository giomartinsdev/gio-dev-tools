from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class IdentityRepository(ABC):
    @abstractmethod
    def get_or_create(self, provider: str, provider_ref: str, entity_type: str) -> UUID: ...
