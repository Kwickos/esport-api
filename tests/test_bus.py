"""Tests for the in-process live event bus."""

from app.bus import InProcessBus


async def test_publish_reaches_subscriber():
    bus = InProcessBus()
    async with bus.subscribe("g1") as sub:
        await bus.publish("g1", {"type": "event", "info": "first blood"})
        msg = await sub.get()
    assert msg == {"type": "event", "info": "first blood"}


async def test_games_are_isolated():
    bus = InProcessBus()
    async with bus.subscribe("g1") as sub1, bus.subscribe("g2") as sub2:
        await bus.publish("g2", {"x": 1})
        assert await sub2.get() == {"x": 1}
        assert sub1._queue.empty()  # g1 received nothing


async def test_subscription_is_cleaned_up():
    bus = InProcessBus()
    async with bus.subscribe("g1"):
        pass
    assert "g1" not in bus._subs  # no lingering subscribers
