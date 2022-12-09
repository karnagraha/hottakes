import asyncio
import datetime
import json
import sqlite3
import datetime

from . import gpt

async def rate_tweet(tweet):
    prompt = """We want to identify the absolute best, most interesting tweets about AI.
We want to identify good tweets about AI, where "good" means it is pro-AI, interesting,
and will get people excited about the future! It must also fit within our content policy.
Content policy:
- No Spam, no hashtag abuse, no advertising.
- No AI risk, safety, xrisk, alignment, etc.
- No AI ethics, equity, fairness, justice, or indigenous rights.
- No climate change, environment, or sustainability.
- No wokeness, racial issues, or social issues.
- No crypto, no NFTs, no DeFi
- No obvious press releases, no obvious marketing. 
- The tweet should be about AI and get people excited about the future!

Consider the following tweet.
    
TWEET:
""" + tweet + """

Please rate this tweet for fit and quality. Answer with a number from 1 to 10 with 1 being the worst and 10 being the best:"""
    return await gpt.send_rate_prompt(prompt)


async def get_summary(tweet):
    prompt = """What is this tweet about? Please briefly summarize it in no more than 20 words.

TWEET: """ + tweet + """
SUMMARY:"""
    return await gpt.send_prompt(prompt)


async def want_write(tweet):
    prompt = """We want to create the best tweets about AI. Below is a tweet.  Do you think this tweet is interesting and notable enough for us to tweet about?
    
TWEET:
""" + tweet + """

Was this tweet good enough for us to use as source material? Answer with "yes" or "no"."""
    return await gpt.send_yn_prompt(prompt)


async def is_repeat(summary):
    history = get_history()
    prompt = """We want to only report new information.
Here is a list of recent tweets we've made plus the tweet we are considering.
Please help us determine if the new tweet is similar to any of the old tweets.

History:
""" + history + """

New tweet:
""" + summary + """

Is this tweet similar to any of the old tweets? Answer with "yes" or "no"."""

    return await gpt.send_yn_prompt(prompt)
    

async def write_tweet(tweet):
    prompt ="""We want to create the best tweets about AI. Below is a tweet. Please write a new
    tweet about the content of this tweet.  Remove extraneous hashtags and mentions.
    Remember:
    - Remove all hashtags.
    - Remove all mentions.

TWEET:
""" + tweet + """
NEW CONTENT:"""
    return await gpt.send_prompt(prompt)

async def handle_tweet(tweet, client):
    url = f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"
    client.loop.create_task(client.get_channel(1047786399266512956).send(url))