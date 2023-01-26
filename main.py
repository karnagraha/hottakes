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
            log.warn("No activity for %d seconds, exiting", max_idle)
            return


async def add_category(filter, category):
    r = await openai.create_embedding(category)
    if r is not None:
        embedding = r["data"][0]["embedding"]
    filter.add_category(category, embedding)


async def create_filter(label, channel, search, categories):
    log.info(f"creating channel {label} {channel} {search} {categories}")
    repeat_threshold = 0.86
    category_threshold = 0.781
    full_search = f"lang:en -is:retweet ({search}) -NFT -mint -crypto -bitcoin -ethereum -drop -airdrop"
    cf = ContentFilter(
        label, channel, repeat_threshold, category_threshold, full_search
    )

    # set up the categories in the embeddings db
    cf.clear_categories()
    for category in categories:
        log.info(f"adding {label} category {category}")
        await add_category(cf, category)
        pass
    return cf


filters = [
    {
        "tag": "companies",
        "channel": 1057190457110712370,
        "filter": "OpenAI OR DeepMind OR GoogleAI",
        "categories": ["openai", "deepmind", "googleai"],
    },
    {
        "tag": "singularity",
        "channel": 1057180785695789086,
        "filter": 'singularity OR transhuman OR technocapital OR "techno capital"',
        "categories": ["singularity", "transhumanism", "technocapital"],
    },
    {
        "tag": "eacc",
        "channel": 1057152611469512767,
        "filter": '"e/acc" OR effective accelerationism',
        "categories": ["e/acc", "effective accelerationism"],
    },
    {
        "tag": "ai",
        "channel": 1047786399266512956,
        "filter": '"artificial intelligence" OR superintelligence OR "super intelligence" OR "Language Model" OR "machine learning"',
        "categories": [
            "artificial intelligence",
            "technocapital",
            "superintelligence",
            "language model",
            "machine learning",
        ],
    },
    {
        "tag": "whitepill",
        "channel": 1048696123121995836,
        "filter": "whitepill OR white pill OR human flourishing OR techno optimism OR techno optimist OR techno-optimism OR futurism OR futurist OR #todayinhistory",
        "categories": [
            "white pill",
            "human flourishing",
            "good news",
            "techno optimism",
            "futurism",
            "today in history",
        ],
    },
]


async def add_filters(dispatcher):
    for f in filters:
        dispatcher.add_filter(
            await create_filter(
                f["tag"],
                f["channel"],
                f["filter"],
                f["categories"],
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
