from dataclasses import dataclass, field


@dataclass
class Station:
    id: str
    name: str
    slug: str
    raw: dict = field(repr=False, default_factory=dict)

    @classmethod
    def from_api(cls, data: dict) -> "Station":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            slug=data.get("slug", ""),
            raw=data,
        )

    def to_dict(self) -> dict:
        return self.raw


@dataclass
class Line:
    id: str
    name: str
    raw: dict = field(repr=False, default_factory=dict)

    @classmethod
    def from_api(cls, data: dict) -> "Line":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            raw=data,
        )

    def to_dict(self) -> dict:
        return self.raw
