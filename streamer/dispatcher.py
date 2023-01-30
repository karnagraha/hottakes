# dispatches tweets from the feed to channels.

import asyncio
import tweepy

from . import eventfilter


class Dispatcher:
    def __init__(self, discord_client, feed):
        """Iniitializes the monitor"""
        self.discord_client = discord_client
        self.feed = feed
        self.filters = {}
        self.rules = []

    def add_filter(self, filter):
        """Adds a content filter to the monitor"""
        self.filters[filter.tag] = filter
        self.rules.append(tweepy.StreamRule(value=filter.get_filter(), tag=filter.tag))

    async def monitor_feed(self):
        """Monitors the twitter feed and dispatches tweets to the proper channel""" ""
        await self.feed.set_rules(self.rules)

        async for event, tag in self.feed:
            asyncio.create_task(self.dispatch(event, tag))

    async def dispatch(self, event, tag):
        """Dispatches an event to the proper channel"""
        filter = self.filters[tag]
        content = await filter.handle_event(event)
        if content is not None:
            for channel_id in filter.channels:
                channel = self.discord_client.get_channel(channel_id)
                await channel.send(content)
