# Discord bot to post twitter feed.

import tweepy
import glog as log

from . import content

class Monitor:
    def __init__(self, discord_client, streamer):
        """Iniitializes the monitor"""
        self.discord_client = discord_client
        self.streamer = streamer

    def add_stream(self, stream):
        """Adds a stream to the monitor"""
        self.streams[stream.tag] = stream
        stream.to_db()

    async def load_streams(self):
        """Loads the configured streams from the database"""
        db = content.DB()
        self.streams = dict([(stream.tag, stream) for stream in db.get_all(self.discord_client)])
        await self.streamer.set_rules(self.get_rules())

    def get_rules(self):
        """Returns a list of rules for the twitter streamer"""
        rules = []     
        for stream in self.streams.values():
            rules.append(tweepy.StreamRule(
                value=stream.get_filter(),
                tag=stream.tag
            ))
        return rules

    async def monitor_stream(self):
        """Monitors the twitter stream and handles tweets"""""
        async for tweet, tag in self.streamer:
            log.info(f"Processing tweet on stream {tag}")
            stream = self.streams[tag]
            await stream.handle_tweet(tweet)