# read twitter feed latest posts
import asyncio
import functools
import json

import tweepy
import tweepy.asynchronous
import streamer


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
    s = streamer.Streamer(get_bearer_token())
    await s.set_rules(rules)
    async for tweet, tag in s:
        print(f"{tweet.user.screen_name} {tweet.full_text}")
        print(f"{tag}, https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}")
        print("======================")

if __name__ == "__main__":
    asyncio.run(main())