import pytest
import asyncio
from streamer.eventfilter import EventFilter
from streamer.dispatcher import Dispatcher


class FakeDiscordClient:
    def __init__(self):
        self.channels = {}

    def get_channel(self, channel_id):
        if channel_id not in self.channels:
            self.channels[channel_id] = FakeChannel(channel_id)
        return self.channels[channel_id]


class FakeChannel:
    def __init__(self, channel_id):
        self.channel_id = channel_id
        self.messages = []

    async def send(self, content):
        print(f"Sending message to channel {self.channel_id}: {content}")
        self.messages.append(content)
        print(f"Messages: {self.messages}")


class FakeFeed:
    def __init__(self, calls=1):
        self.rules = []
        self.calls = calls

    async def set_rules(self, rules):
        self.rules = rules

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.calls:
            self.calls -= 1
            return {"url": "http://foo.com", "text": "foo"}, "test"
        else:
            raise StopAsyncIteration


def get_event_filter(channel_id=1):
    return EventFilter(
        tag="test",
        channels=[1],
        filter="",
        repeat_db=None,
        classifier=None,
    )


@pytest.mark.asyncio
async def test_monitor_feed():
    discord = FakeDiscordClient()
    feed = FakeFeed(5)
    dispatcher = Dispatcher(discord, feed)
    ef = get_event_filter()
    dispatcher.add_filter(ef)

    await dispatcher.monitor_feed()
    await asyncio.sleep(0.1)
    channel = discord.get_channel(1)
    assert len(channel.messages) == 5


@pytest.mark.asyncio
async def test_multichannel_dispatch():
    discord = FakeDiscordClient()
    feed = FakeFeed(5)
    dispatcher = Dispatcher(discord, feed)
    ef = get_event_filter()
    ef.channels.append(2)
    dispatcher.add_filter(ef)

    await dispatcher.monitor_feed()
    await asyncio.sleep(0.1)
    channel1 = discord.get_channel(1)
    channel2 = discord.get_channel(2)
    assert len(channel1.messages) == 5
    assert len(channel2.messages) == 5


@pytest.mark.asyncio
async def test_multiple_filters():
    discord = FakeDiscordClient()
    feed = FakeFeed(5)
    dispatcher = Dispatcher(discord, feed)
    ef1 = get_event_filter()
    ef2 = get_event_filter()
    ef2.tag = "test2"
    ef2.channels = [2]
    dispatcher.add_filter(ef1)
    dispatcher.add_filter(ef2)

    await dispatcher.monitor_feed()
    await asyncio.sleep(0.1)
    channel1 = discord.get_channel(1)
    channel2 = discord.get_channel(2)
    assert len(channel1.messages) == 5
    assert len(channel2.messages) == 0
