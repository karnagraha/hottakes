import asyncio
import datetime
import json
import re
import glog as log

import discord
import asyncopenai.asyncopenai as openai

import streamer.streamer as streamer
import streamer.monitor as monitor
from streamer.channel import Content

def get_bot_token():
    with open("discord_secrets.json") as f:
        secrets = json.load(f)
    return secrets["bot_token"]

client = discord.Client(intents=discord.Intents.default())

# on_ready initializes the bot and starts the streamer
@client.event
async def on_ready():
    log.info(f"We have logged in as {client.user}, initiating streamer")
    s = streamer.Streamer(streamer.get_bearer_token())
    log.info(f"initializing monitor")
    m = monitor.Monitor(client, s)
    log.info(f"loading content channels")
    await m.load_channels()
    log.info("Monitoring stream.")
    asyncio.get_event_loop().create_task(m.monitor_streamer())

@client.event
async def on_reaction_add(reaction, user):
    if reaction.message.author != client.user:
        return

    match = re.search(r"https://twitter.com/[^/]+/status/(\d+)", reaction.message.content)
    if match:
        url = match.group(0)
        log.info(f"User {user} reacted to {url}")

@client.event
async def on_message(message):
    log.info(f"#{message.channel.name}:{message.channel.id} <{message.author}> {message.content}")
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

async def add_category(stream, category):
    r = await openai.create_embedding(category)
    if r is not None:
        embedding = r["data"][0]["embedding"]
    stream.add_category(category, embedding)

def create_channel(label, channel, search, categories):
    log.info(f"creating channel {label} {channel} {search} {categories}")
    repeat_threshold = 0.86
    category_threshold = 0.781
    full_search = f"lang:en -is:retweet ({search}) -NFT -mint -crypto -bitcoin -ethereum -drop -airdrop"
    c = Content(client, label, channel, repeat_threshold, category_threshold, full_search)
    c.to_db()
    c.clear_categories()
    for category in categories:
        log.info(f"adding {label} category {category}")
        asyncio.run(add_category(c, category))
        pass
    return c

def main():
    # create initial content stream rules.


    create_channel(
        "companies",
        1047786399266512956,
        "OpenAI or DeepMind or GoogleAI",
        ["openai", "deepmind", "googleai"]
    )
    create_channel(
        "singularity",
        1057180785695789086,
        "singularity OR transhuman OR technocapital OR techno-capital",
        ["singularity", "transhumanism", "technocapital"],
    )
    create_channel(
        "eacc",
        1057152611469512767,
        '"e/acc" OR effective accelerationism',
        ["e/acc", "effective accelerationism"],
    )
    create_channel(
        "ai",
        1047786399266512956,
        'artificial intelligence OR technocapital OR techno capital OR superintelligence OR super intelligence OR LLM OR Language Model or ML',
        ["artificial intelligence", "technocapital", "superintelligence", "LLM", "Language Model", "ML"],
    )
    create_channel(
        "whitepill",
        1048696123121995836,
        "whitepill OR white pill OR human flourishing OR techno optimism OR techno optimist OR techno-optimism OR futurism OR futurist OR #todayinhistory",
        ["white pill", "human flourishing", "good news", "techno optimism", "futurism", "today in history"],
    )


    # this starts everything.
    c = client.run(get_bot_token())

    # wait for all tasks to exit
    loop = asyncio.get_event_loop()
    loop.run_until_complete(activity_check())
    loop.close()


if __name__ == "__main__":
    main()
