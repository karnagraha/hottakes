# read twitter feed latest posts
import asyncio
import functools
import json

import tweetdb
import tweepy
import tweepy.asynchronous
import glog as log

class Streamer(tweepy.asynchronous.AsyncStreamingClient):
    def __init__(self, bearer_token, **kwargs):
        super().__init__(bearer_token, **kwargs)
        self.started = False
        self.queue = asyncio.Queue()

        auth = tweepy.OAuth2BearerHandler(bearer_token)
        self.api = tweepy.API(auth)
        self.tweetdb = tweetdb.TweetDB(self.api)

    def start(self):
        """This starts a background task for the streamer, but you still need to
        start asyncio's event loop"""
        if not self.started:
            self.started = True
            self.filter()

    def __aiter__(self):
        if not self.started:
            self.start()
        return self
    
    async def __anext__(self):
        return await self.queue.get()
    
    async def on_connect(self):
        log.info("Connected to Twitter streaming API")

    async def on_data(self, data):
        data = json.loads(data)
        try:
            tag = data["matching_rules"][0]["tag"]
            tweet = data["data"]
        except (KeyError, IndexError) as e:
            log.warn(f"Error reading stream content: {e}")
            return
        log.info(f"Received tweet {tweet['id']} on tag {tag}")
        
        tweet = self.tweetdb.get_tweet(tweet["id"])
        if tweet is None:
            log(f"Failed to get_tweet for {tweet['id']}")
            return

        # enqueue tweet and tag
        await self.queue.put((tweet, tag))

    async def set_rules(self, new_rules):
        # get the existing rules
        rules = await self.get_rules()
        # TODO this should merge the two sets of rules
        if rules.data:
            for rule in rules.data:
                await self.delete_rules(rule.id)
        # add the new rules
        for rule in new_rules:
            await self.add_rules(rule)

    async def on_error(self, status_code):
        log("Error from Twitter: %s" % status_code)

    async def on_timeout(self):
        log("Timeout from Twitter")
        return True  # Don't kill the stream

@functools.lru_cache(maxsize=None)
def get_bearer_token():
    # get bearer token from twitter_secrets.json
    with open("twitter_secrets.json") as f:
        secrets = json.load(f)
    bearer_token = secrets["bearer_token"]
    return bearer_token