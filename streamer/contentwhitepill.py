import asyncio
import datetime
import json
import sqlite3
import datetime

from . import gpt


async def classify(tweet):
    prompt = """We want to identify the absolute best, most interesting and inspiring tweets.
We are looking for "whitepill" content.  Whitepill means it is an antidote to cynicism, doomerism and blackpill thinking. Whitepill means it will get people excited about life, the future, and the potential of humanity. It must also fit within our content policy.
CONTENT POLICY:
- No obvious press releases, no obvious marketing.
- No wokeness, racial issues, or social issues.
- Definitely include: good whitepill tweets, tweets that are optimistic about the future, and tweets celebrating the past.

Consider the following tweet.
    
TWEET:
""" + tweet + """

Was this a good inspiring tweet? Answer with "yes" or "no"."""
    return await gpt.send_yn_prompt(prompt)


async def handle_tweet(tweet, client):
    # tweeter
    full_tweet = f"{tweet.user.name} (@{tweet.user.screen_name}): {tweet.full_text}"
    url = f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"
    msg = f"URL: {url}"
    if await classify(full_tweet):
        msg = "✅ " + msg
    client.loop.create_task(client.get_channel(1048696123121995836).send(msg))