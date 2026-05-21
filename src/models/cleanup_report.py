from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CleanupReport:
    moved_count: int
    protected_count: int
    estimated_space_bytes: int
