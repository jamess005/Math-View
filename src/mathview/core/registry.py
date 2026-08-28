"""Topic name to generator lookup.

A topic generator has the signature:

    (rows: list[str], params: dict[str, float]) -> Sequence

Adding a module means registering one of these. The engine, the shell and the
view toggle never change.
"""

from __future__ import annotations

from collections.abc import Callable

from mathview.core.step import Sequence

TopicGenerator = Callable[[list[str], dict[str, float]], Sequence]

_TOPICS: dict[str, TopicGenerator] = {}


class UnknownTopicError(KeyError):
    """Asked for a topic nobody registered."""


def register_topic(name: str, generator: TopicGenerator) -> None:
    _TOPICS[name] = generator


def get_topic(name: str) -> TopicGenerator:
    try:
        return _TOPICS[name]
    except KeyError as exc:
        raise UnknownTopicError(name) from exc


def available_topics() -> list[str]:
    return sorted(_TOPICS)
