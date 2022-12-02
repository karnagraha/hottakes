# Discord bot to post twitter feed.
import asyncio
import datetime
import json
import sqlite3

import discord
import tweepy

from . import gpt
from . import tweetstreamer

def get_history():
    # get history from db
    db = get_db()
    c = db.cursor()
    # select the last 50 messages by timestamp, where the summary field isn't empty and it is not a repeat.
    rows = c.execute("SELECT * FROM tweets WHERE summary != '' AND repeat = 0 ORDER BY timestamp DESC LIMIT 50").fetchall()
    return "\n".join([f"- {row[0]}" for row in rows])

def get_db():
    conn = sqlite3.connect("tweets.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS tweets (
        id integer PRIMARY KEY,
        timestamp text NOT NULL,
        tweet text NOT NULL,
        rewrite text NOT NULL, 

        rating integer NOT NULL,
        repeat integer NOT NULL,
        summary text NOT NULL,
        url text NOT NULL
    );""")
    conn.commit()
    return conn



def classify(tweet):
    prompt = """We want to identify the absolute best, most interesting tweets about AI.
We want to identify good tweets about AI, where "good" means it is pro-AI, interesting,
and will get people excited about the future! It must also fit within our content policy.
Content policy:
- No Spam, no hashtag abuse, no advertising.
- No AI risk, safety, xrisk, alignment, etc.
- No AI ethics, equity, fairness, justice, or indigenous rights.
- No climate change, environment, or sustainability.
- No wokeness, racial issues, or social issues.
- No Crypto
- The tweet should be about AI and get people excited about the future!

Consider the following tweet.
    
TWEET:
""" + tweet + """

Was this a good tweet about AI? Answer with "yes" or "no"."""
    return gpt.send_yn_prompt(prompt)

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
- No crypto
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

# create a sql database to store tweet data in
# get db handle
# write tweet to db
def write_tweet_to_db(tweet, rewrite, rating, repeat, summary, url):
    timestamp = datetime.datetime.now()
    db = get_db()
    c = db.cursor()
    c.execute("INSERT INTO tweets VALUES (NULL, ?, ?, ?, ?, ?, ?, ?)", (timestamp, tweet, rewrite, rating, repeat, summary, url))

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
        # tweeter
        full_tweet = f"{tweet.user.name} (@{tweet.user.screen_name}): {tweet.full_text}"
        rating = await rate_tweet(full_tweet)
        if rating >= 8 and await want_write(full_tweet):
            summary = await get_summary(full_tweet)
            repeat = await is_repeat(summary)
            newtweet = await write_tweet(full_tweet)
            url = f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"
            write_tweet_to_db(full_tweet, newtweet, rating, repeat, summary, url)
            if repeat:
                continue
            msg = f"✳️✳️✳️✳️✳️✳️✳️✳️✳️✳️✳️✳️✳️✳️✳️✳️✳️✳️✳️✳️✳️✳️✳️✳️\nSUMMARY: {summary}\nRATING: {rating}\nREPEAT: {repeat}\nORIGINAL: {full_tweet}\nUPDATED: {newtweet}\nURL: {url}"
            client.loop.create_task(client.get_channel(1047786399266512956).send(msg))
        else:
            write_tweet_to_db(full_tweet, "", rating, 0, "", "")

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
    client.loop.create_task(client.get_channel(1047786399266512956).send("Online."))
    asyncio.get_event_loop().create_task(monitor_stream(client))

@client.event
async def on_message(message):
    url = re.search(r"https://twitter.com/[^/]+/status/(\d+)", message.content)
    if url:
        print(f"URL: {url}")
    if message.author == client.user:
        # extract tweet url from message
        url = re.search(r"https://twitter.com/[^/]+/status/(\d+)", message.content)
        print(f"URL: {url}")

        try:
            reaction, user = await client.wait_for('reaction_add', timeout=60.0)
        except asyncio.TimeoutError:
            pass
        else:
            print(f"Reaction: {reaction}")
            print(f"User: {user}")

        # wait for a reaction.
        return
    else:
        # print message and channel id
        print(f"Message: {message.content} Channel: {message.channel.id}")