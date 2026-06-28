from abc import ABC, abstractmethod

from .quote_event import QuoteEvent


class QuoteEventRepository(ABC):
    @abstractmethod
    def save_all(self, events: list[QuoteEvent]) -> None: ...

    @abstractmethod
    def find_latest_per_ticker(self) -> list[QuoteEvent]: ...

    @abstractmethod
    def get_asset_tickers(self) -> list[str]: ...
