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
            value='lang:en -is:retweet -is:reply -NFT (artificial intelligence OR technocapital OR ai safety OR superintelligence OR transhumanism OR transhumanist OR "e/acc" OR effective accelerationism) -mint -nft -crypto -bitcoin -ethereum',
            tag="ai"
        ),
        tweepy.StreamRule(
            value="lang:en -is:retweet (whitepill OR white pill OR human flourishing OR techno optimism OR techno optimist OR techno-optimism OR futurism OR futurist OR #todayinhistory OR cybernetic) -mint -nft -crypto -bitcoin -ethereum",
            tag="whitepill"
        ),
    ]

    s = tweetstreamer.Streamer(tweetstreamer.get_bearer_token())
    await s.set_rules(rules)
    async for tweet, tag in s:
        url = f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"
        if tweet.in_reply_to_status_id is not None:
            print(f"Skipping reply: {url}")
            continue
        elif tag == "ai":
            await contentai.handle_tweet(tweet, client)
        elif tag == "whitepill":
            await contentwhitepill.handle_tweet(tweet, client)
        else:
            print(f"Unknown tag: {tag}")