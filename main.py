import asyncio
import datetime
import json
import re
import glog as log
import unicodedata

import discord
import asyncopenai.asyncopenai as openai

from streamer.twitterfeed import TwitterFeed
from streamer.eventfilter import EventFilter
from streamer.dispatcher import Dispatcher
from streamer.tweetdb import TweetDB
from streamer.repeatdb import RepeatDB
from classifier import client as classifier_client


def get_bot_token():
    with open("discord_secrets.json") as f:
        secrets = json.load(f)
    return secrets["bot_token"]


client = discord.Client(intents=discord.Intents.default())

# on_ready initializes the bot and starts the streamer
@client.event
async def on_ready():
    log.info(f"We have logged in as {client.user}")
    log.info("initializing feed")
    feed = TwitterFeed()

    log.info(f"initializing dispatcher")
    dispatcher = Dispatcher(client, feed)

    log.info(f"adding content filters")
    await add_filters(dispatcher)

    log.info("Monitoring stream.")
    asyncio.get_event_loop().create_task(dispatcher.monitor_feed())


# the way we are sending messages, they are not being added to the
# cache, so we need to retrieve messages in order to parse them when
# a reaction occurs.
@client.event
async def on_raw_reaction_add(payload):
    channel = client.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    emoji = payload.emoji

    try:
        character = unicodedata.name(emoji.name)
    except (TypeError, ValueError):
        log.info(f"skipping reaction {emoji.name}: non-unicode response.")
        return

    # parse the message content
    if message.author != client.user:
        log.info(f"skipping reaction {character}: not author")
        return

    match = re.search(r"https://twitter.com/i/web/status/(\d+)", message.content)
    if match:
        url = match.group(0)
    else:
        log.info(f"skipping reaction {character}: improperly formatted message")
        return

    log.info(f"Saving reaction {character} to {url}")
    tdb = TweetDB()
    # save the reaction text to the database
    tdb.set_reaction(url, emoji.name)


@client.event
async def on_message(message):
    log.info(
        f"#{message.channel.name}:{message.channel.id} <{message.author}> {message.content}"
    )
    if message.author == client.user:
        activity = datetime.datetime.now()
        return


# for stall detection
activity = datetime.datetime.now()

# We get stalls on the twitter feed, this is a workaround for now.
# TODO: we seem to stall out sometimes for other reasons as well, this needs more investigation.
async def activity_check(max_idle=600):
    global activity
    while True:
        await asyncio.sleep(10)
        max_age = datetime.datetime.now() - datetime.delta(seconds=max_idle)
        if activity < max_age:
            log.warn(f"No activity for {max_idle} seconds, exiting")
            return


async def create_filter(
    tag, channels, search, check_classifier, check_repeats, enforce_classifier
):
    log.info(f"creating filter {tag} {channels} {search}")
    full_search = f"lang:en -is:retweet ({search}) -NFT -DEX -mint -crypto -bitcoin -ethereum -drop -airdrop"
    cf = EventFilter(
        tag,
        channels,
        full_search,
        classifier=classifier_client if check_classifier else None,
        repeat_db=RepeatDB(tag) if check_repeats else None,
        enforce_classifier=enforce_classifier,
    )
    return cf


filters = [
    {
        "tag": "eacc",
        "channels": [1057152611469512767, 1068439457751126089],
        "filter": '"e/acc" OR "effective accelerationism" OR "effective accelerationist" OR from:basedbeffjezos OR from:bayeslord',
        "check_classifier": False,
        "enforce_classifier": False,
        "check_repeats": False,
    },
    {
        "tag": "ai",
        "channels": [1047786399266512956],
        "filter": '"artificial intelligence" OR superintelligence OR "super intelligence" OR "Language Model" OR "machine learning" OR openai OR google-research OR arxiv OR deepmind OR googleresearch OR arxiv OR "large language model" OR LLM OR LLMS OR RLHF OR RLAIF OR LaMDa',
        "check_classifier": True,
        "enforce_classifier": True,
        "check_repeats": False,
    },
    {
        "tag": "whitepill",
        "channels": [1048696123121995836],
        "filter": 'whitepill OR "white pill" OR human flourishing OR "techno optimism" OR "techno optimist" OR futurism OR futurist OR #todayinhistory',
        "check_classifier": True,
        "enforce_classifier": False,
        "check_repeats": False,
    },
]


# TODO: pass dict into create_filter
async def add_filters(dispatcher):
    for f in filters:
        dispatcher.add_filter(
            await create_filter(
                f["tag"],
                f["channels"],
                f["filter"],
                f["check_classifier"],
                f["check_repeats"],
                f["enforce_classifier"],
            )
        )


def main():
    # this starts everything.
    c = client.run(get_bot_token())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(activity_check())
    loop.close()


if __name__ == "__main__":
    main()
