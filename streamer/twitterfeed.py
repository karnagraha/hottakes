# read twitter feed latest posts
import asyncio
import functools
import json

import tweepy
import tweepy.asynchronous
import glog as log

from streamer.tweetdb import TweetDB


@functools.lru_cache(maxsize=None)
def get_bearer_token():
    # get bearer token from twitter_secrets.json
    with open("twitter_secrets.json") as f:
        secrets = json.load(f)
    bearer_token = secrets["bearer_token"]
    return bearer_token


@functools.lru_cache(maxsize=None)
def get_api(bearer_token):
    auth = tweepy.OAuth2BearerHandler(bearer_token)
    api = tweepy.API(auth)
    return api


class TwitterFeed(tweepy.asynchronous.AsyncStreamingClient):
    def __init__(self, **kwargs):
        self.bearer_token = get_bearer_token()
        super().__init__(self.bearer_token, **kwargs)
        self.started = False
        self.queue = asyncio.Queue()
        self.api = get_api(self.bearer_token)
        self.tweetdb = TweetDB()

    async def set_rules(self, new_rules):
        log.info(f"Setting rules to {new_rules}.")
        # TODO this should merge the two sets of rules
        # because modifying filter rules is aggressively rate limited

        # get the existing rules
        log.info(f"Getting existing rules.")
        rules = await self.get_rules()
        if rules.data:
            for rule in rules.data:
                log.info(f"Deleting rule {rule.id} {rule.tag} {rule.value}.")
                await self.delete_rules(rule.id)
        # add the new rules
        for rule in new_rules:
            log.info(f"Adding rule {rule.tag} {rule.value}.")
            await self.add_rules(rule)
        log.info(f"Done setting rules.")

    def __aiter__(self):
        if not self.started:
            self.started = True
            self.filter()
        return self

    def get_tweet(self, id):
        """Get a tweet from twitter, bypassing the database.
        Returns a tweepy.models.Status object, or None if error."""
        try:
            tweet = self.api.get_status(id, tweet_mode="extended")
        except tweepy.TweepyException as e:
            log.warn(f"Failed to retrieve tweet {id}: {e}")
            return None
        return tweet

    def get_qsize(self):
        return self.queue.qsize()

    async def __anext__(self):
        return await self.queue.get()

    async def on_connect(self):
        log.info("Connected to Twitter streaming API")

    async def on_error(self, status_code):
        log.info("Error from Twitter: %s" % status_code)
        return True

    async def on_timeout(self):
        log.info("Timeout from Twitter")
        return True  # Don't kill the stream

    async def on_data(self, data):
        data = json.loads(data)
        try:
            rules = data["matching_rules"]
            id = data["data"]["id"]
            text = data["data"]["text"]
            url = f"https://twitter.com/i/web/status/{id}"
        except KeyError as e:
            log.warn(f"Error reading stream content: {e}")
            return

        event = {
            "id": id,
            "text": text,
            "url": url,
        }
        for tag in rules:
            await self.queue.put((event, tag["tag"]))
            qsize = self.get_qsize()
            if qsize > 10:
                log.info(f"[{tag['tag']}] queued tweet {id} (qsize: {qsize})")

        # save the first tag in rules, along with the url and the full text
        tag = rules[0]["tag"]
        try:
            self.tweetdb.add(text, url, tag)
        except sqlite3.IntegrityError as e:
            # it's apparently not safe to assume that these are unique from the feed.
            log.warn(f"Error saving tweet {id}: {e}")
            return
