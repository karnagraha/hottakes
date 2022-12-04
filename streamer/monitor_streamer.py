# Discord bot to post twitter feed.


import tweepy

from . import tweetstreamer
from . import contentai
from . import contentwhitepill


async def monitor_stream(client):
    # rule format
    # https://developer.twitter.com/en/docs/twitter-api/tweets/filtered-stream/integrate/build-a-rule
    rules = [
        tweepy.StreamRule(
            value="lang:en -is:retweet -NFT (artificial intelligence OR technocapital OR ai safety OR superintelligence) -nft -crypto -bitcoin -ethereum",
            tag="ai"
        ),
        tweepy.StreamRule(
            value="lang:en -is:retweet (whitepill OR human flourishing OR technooptimism OR futurism OR cyberpunk) -nft -crypto -bitcoin -ethereum -edgerunners -2077",
            tag="whitepill"
        )
    ]
    s = tweetstreamer.Streamer(tweetstreamer.get_bearer_token())
    await s.set_rules(rules)
    async for tweet, tag in s:
        url = f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"
        if tweet.in_reply_to_status_id is not None:
            print(f"Skipping reply: {url}")
            continue
        if tag == "ai":
            await contentai.handle_tweet(tweet, client)
        elif tag == "whitepill":
            await contentwhitepill.handle_tweet(tweet, client)
        else:
            print(f"Unknown tag: {tag}")