from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImageSpec:
    """A single generated square PNG asset."""

    filename: str
    size: int
    padding: float = 0.0
    background: tuple[int, int, int, int] = (0, 0, 0, 0)


@dataclass(frozen=True)
class IcoSpec:
    """A multi-resolution .ico asset bundling several square sizes into one file."""

    filename: str
    sizes: tuple[int, ...]
    padding: float = 0.0


@dataclass(frozen=True)
class CanvasImageSpec:
    """A single generated PNG asset on a non-square width x height canvas."""

    filename: str
    width: int
    height: int
    padding: float = 0.0
    background: tuple[int, int, int, int] = (0, 0, 0, 0)
