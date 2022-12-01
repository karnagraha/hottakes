# Discord bot to post twitter feed.
import asyncio
import json

import discord
import tweepy

from . import gpt
from . import tweetstreamer


def classify(tweet):
    prompt = """We want to identify the absolute best, most interesting tweets about AI. We're looking for good content, not just advertising.  We are very PRO-AI! We only want content that encourages people to think well about AI or be excited about it. We don't talk about risk, safety, equity, fairness, or justice. Please rate the following tweets.
    
TWEET:
""" + tweet + """

Was this a good tweet about AI? Answer with "yes" or "no"."""
    return gpt.send_yn_prompt(prompt)

def want_write(tweet):
    prompt = """We want to create the best tweets about AI. Below is a tweet.  Do you think this tweet is interesting and notable enough for us to tweet about?
    
TWEET:
""" + tweet + """

Was this tweet good enough for us to use as source material? Answer with "yes" or "no"."""
    return gpt.send_yn_prompt(prompt)

def write_tweet(tweet):
    prompt ="""We want to create the best tweets about AI. Below is a tweet. Please rewrite it to make it better. Do not use hashtags.

TWEET:
""" + tweet + """
REWRITE:"""
    return gpt.send_prompt(prompt)

async def monitor_stream(client):
    # rule format
    # https://developer.twitter.com/en/docs/twitter-api/tweets/filtered-stream/integrate/build-a-rule
    rules = [
        tweepy.StreamRule(
            value="lang:en -is:retweet (artificial intelligence OR technocapital OR ai safety OR superintelligence)",
            tag="ai"
        )
    ]
    s = tweetstreamer.Streamer(tweetstreamer.get_bearer_token())
    await s.set_rules(rules)
    async for tweet, unused_tag in s:
        if classify(tweet.full_text):
            if want_write(tweet.full_text):
                report_tweet(client, write_tweet(tweet.full_text), tweet)

def report_tweet(client, text, orig):
    url = f"https://twitter.com/{orig.user.screen_name}/status/{orig.id}"
    client.loop.create_task(client.get_channel(1047786399266512956).send(f"{text}\n{url}"))

# load credentials from json file
def get_bot_token():
    with open("discord_secrets.json") as f:
        secrets = json.load(f)
    return secrets["bot_token"]

client = discord.Client(intents=discord.Intents.default())
# authenticate discord client
def get_client():
    return client

@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")
    asyncio.get_event_loop().create_task(monitor_stream(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    # print message and channel id
    print(f"Message: {message.content} Channel: {message.channel.id}")