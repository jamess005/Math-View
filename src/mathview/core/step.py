"""The one shape everything in MathView is displayed as.

A topic generator turns user input into a Sequence of Steps. Every Step has the
same three faces - notation, prose, visual - any of which may be absent. The
view toggle in the UI can switch between them uniformly precisely because no
topic is allowed to vary this shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class VisualSpec:
    """A declarative drawing instruction. Python never draws; it emits these.

    `kind` selects a renderer in the frontend's registry; `data` is whatever
    that renderer needs. Adding a new visual means adding a kind and a renderer,
    and touching nothing else.
    """

    kind: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, **self.data}


@dataclass(frozen=True)
class Step:
    """One step of a sequence. Any face may be absent."""

    index: int
    title: str
    notation: str | None = None
    prose: str | None = None
    visual: VisualSpec | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "title": self.title,
            "notation": self.notation,
            "prose": self.prose,
            "visual": self.visual.to_dict() if self.visual is not None else None,
        }


@dataclass(frozen=True)
class Sequence:
    """An ordered list of steps produced by one topic from one input."""

    topic: str
    steps: tuple[Step, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"topic": self.topic, "steps": [s.to_dict() for s in self.steps]}
