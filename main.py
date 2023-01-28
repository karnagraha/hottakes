import asyncio
import datetime
import json
import re
import glog as log

import discord
import asyncopenai.asyncopenai as openai

from streamer.twitterfeed import TwitterFeed
from streamer.contentfilter import ContentFilter
from streamer.dispatcher import Dispatcher
from streamer.tweetdb import TweetDB


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


@client.event
async def on_reaction_add(reaction, user):
    log.info(f"User {user} reacted {reaction}")
    if reaction.message.author != client.user:
        return

    match = re.search(
        r"https://twitter.com/[^/]+/status/(\d+)", reaction.message.content
    )
    if match:
        url = match.group(0)
        log.info(f"User {user} reacted {reaction} to {url}")
        tdb = TweetDB()
        # save the reaction text to the database
        tdb.set_reaction(url, str(reaction))


@client.event
async def on_message(message):
    log.info(
        f"#{message.channel.name}:{message.channel.id} <{message.author}> {message.content}"
    )
    if message.author == client.user:
        activity = datetime.datetime.now()
        return
    if not message.guild:
        await message.channel.send("Thanks for the DM!")


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


async def create_filter(tag, channels, search, check_classifier, check_repeats):
    log.info(f"creating filter {tag} {channels} {search}")
    repeat_threshold = 0.86
    full_search = f"lang:en -is:retweet ({search}) -NFT -mint -crypto -bitcoin -ethereum -drop -airdrop"
    cf = ContentFilter(
        tag,
        channels,
        repeat_threshold,
        full_search,
        check_classifier,
        check_repeats,
    )
    return cf


filters = [
    {
        "tag": "eacc",
        "channels": [1057152611469512767, 1068439457751126089],
        "filter": '"e/acc" OR effective accelerationism',
        "check_classifier": False,
        "check_repeats": False,
    },
    {
        "tag": "ai",
        "channels": [1047786399266512956],
        "filter": '"artificial intelligence" OR superintelligence OR "super intelligence" OR "Language Model" OR "machine learning" OR openai OR google-research OR arxiv OR deepmind OR googleresearch',
        "check_classifier": True,
        "check_repeats": True,
    },
    {
        "tag": "whitepill",
        "channels": [1048696123121995836],
        "filter": 'whitepill OR white pill OR optimism OR human flourishing OR "techno optimism" OR optimist OR "techno optimist" OR futurism OR futurist OR #todayinhistory',
        "check_classifier": False,
        "check_repeats": True,
    },
]


async def add_filters(dispatcher):
    for f in filters:
        dispatcher.add_filter(
            await create_filter(
                f["tag"],
                f["channels"],
                f["filter"],
                f["check_classifier"],
                f["check_repeats"],
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
