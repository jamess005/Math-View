"""Topic lookup: the seam that lets modules be added without engine changes."""

import pytest

from mathview.core.registry import (
    UnknownTopicError,
    available_topics,
    get_topic,
    register_topic,
)
from mathview.core.step import Sequence


def _dummy(rows, params):
    return Sequence(topic="dummy", steps=())


def test_registered_topic_can_be_fetched():
    register_topic("dummy", _dummy)

    assert get_topic("dummy") is _dummy


def test_unknown_topic_raises():
    with pytest.raises(UnknownTopicError):
        get_topic("no-such-topic")


def test_available_topics_is_sorted():
    register_topic("zebra", _dummy)
    register_topic("alpha", _dummy)

    names = available_topics()
    assert names == sorted(names)
    assert "alpha" in names and "zebra" in names
