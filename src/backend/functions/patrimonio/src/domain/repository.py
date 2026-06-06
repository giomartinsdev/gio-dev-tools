from abc import ABC, abstractmethod
from typing import Optional

from .asset import Asset


class AssetRepository(ABC):
    @abstractmethod
    def save(self, asset: Asset) -> None: ...

    @abstractmethod
    def delete(self, asset_id: str) -> bool: ...

    @abstractmethod
    def find_all(self) -> list[Asset]: ...

    @abstractmethod
    def find_by_id(self, asset_id: str) -> Optional[Asset]: ...
