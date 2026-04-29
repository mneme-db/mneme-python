from dataclasses import dataclass


@dataclass(frozen=True)
class SearchResult:
    id: str
    score: float
