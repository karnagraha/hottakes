# Discord bot to post twitter feed.

import tweepy
import glog as log

from . import channel

class Monitor:
    def __init__(self, discord_client, streamer):
        """Iniitializes the monitor"""
        self.discord_client = discord_client
        self.streamer = streamer
        self.channels = {}

    def add_channel(self, channel):
        """Adds a content channel to the monitor"""
        self.channels[channel.tag] = channel
        channel.to_db()

    async def load_channels(self):
        """Loads the configured content channels from the database"""
        db = channel.DB()
        self.channels = dict([(channel.tag, channel) for channel in db.get_all(self.discord_client)])
        await self.streamer.set_rules(self.get_rules())

    def get_rules(self):
        """Returns a list of rules for the twitter streamer"""
        rules = []     
        for channel in self.channels.values():
            rules.append(tweepy.StreamRule(
                value=channel.get_filter(),
                tag=channel.tag
            ))
        return rules

    async def monitor_streamer(self):
        """Monitors the twitter stream and dispatches tweets to the proper channel"""""
        async for tweet, tag in self.streamer:
            log.info(f"Processing tweet on channel {tag}")
            channel = self.channels[tag]
            await channel.handle_tweet(tweet)