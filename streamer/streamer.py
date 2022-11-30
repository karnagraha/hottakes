# read twitter feed latest posts
import asyncio
import functools
import json

import tweepy
import tweepy.asynchronous

class Streamer(tweepy.asynchronous.AsyncStreamingClient):
    def __init__(self, bearer_token, **kwargs):
        super().__init__(bearer_token, **kwargs)
        self.started = False
        self.queue = asyncio.Queue()

        auth = tweepy.OAuth2BearerHandler(bearer_token)
        self.api = tweepy.API(auth)

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
        print("Connected to streaming API")

    async def on_data(self, data):
        data = json.loads(data)
        tag = data["matching_rules"][0]["tag"]
        tweet = data["data"]

        # there is no async call to get the full text of the tweet
        try:
            tweet = self.api.get_status(tweet["id"], tweet_mode="extended")
        except tweepy.TweepyException as e:
            print("error getting tweet: {e}")
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
        print(status_code)

    async def on_timeout(self):
        print("Timeout...")
        return True  # Don't kill the stream

@functools.lru_cache(maxsize=None)
def get_bearer_token():
    # get bearer token from twitter_secrets.json
    with open("twitter_secrets.json") as f:
        secrets = json.load(f)
    bearer_token = secrets["bearer_token"]
    return bearer_token

async def main():
    # rule format
    # https://developer.twitter.com/en/docs/twitter-api/tweets/filtered-stream/integrate/build-a-rule
    rules = [
        tweepy.StreamRule(
            value="lang:en -is:retweet -#AfricanAI (from:xlr8harder OR to:xlr8harder OR artificial intelligence OR technocapital OR ai safety OR superintelligence)",
            tag="ai"
        )
    ]
    streamer = Streamer(get_bearer_token())
    await streamer.set_rules(rules)
    async for tweet, tag in streamer:
        print(f"{tweet.user.screen_name} {tweet.full_text}")
        print(f"{tag}, https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}")
        print("======================")

if __name__ == "__main__":
    asyncio.run(main())