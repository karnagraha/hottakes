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
        log.info(f"Retrieving tweet {id} from Twitter")
        try:
            tweet = self.api.get_status(id, tweet_mode="extended")
        except tweepy.TweepyException as e:
            log.warn(f"Failed to retrieve tweet {id}: {e}")
            return None
        return tweet

    async def __anext__(self):
        return await self.queue.get()

    async def on_connect(self):
        log.info("Connected to Twitter streaming API")

    async def on_error(self, status_code):
        log("Error from Twitter: %s" % status_code)
        return True

    async def on_timeout(self):
        log("Timeout from Twitter")
        return True  # Don't kill the stream

    async def on_data(self, data):
        data = json.loads(data)
        try:
            rules = data["matching_rules"]
            id = data["data"]["id"]
        except KeyError as e:
            log.warn(f"Error reading stream content: {e}")
            return

        try:
            content = self.get_tweet(id)
        except KeyError:
            log.info(f"Received non-tweet {id}")
            return
        if content is None:
            log.info(f"Failed to get_tweet for {id}")
            return

        for tag in rules:
            log.info(f"Received tweet {id} on tag {tag['tag']}")
            await self.queue.put((content, tag["tag"]))

        # save the first tag in rules, along with the url and the full text
        tag = rules[0]["tag"]
        url = f"https://twitter.com/{content.user.screen_name}/status/{content.id}"
        full_text = content.full_text
        self.tweetdb.add(full_text, url, tag)
