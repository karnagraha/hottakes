import asyncio
import datetime
import json
import re
import glog as log

import discord
import asyncopenai.asyncopenai as openai

import streamer.streamer as streamer
import streamer.monitor as monitor
from streamer.content import Content

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
    log.info(f"loading streams")
    await m.load_streams()
    log.info("Monitoring streams.")
    asyncio.get_event_loop().create_task(m.monitor_stream())

@client.event
async def on_reaction_add(reaction, user):
    if reaction.message.author != client.user:
        return

    print(f"reaction added: {reaction}")
    match = re.search(r"https://twitter.com/[^/]+/status/(\d+)", reaction.message.content)
    if match:
        url = match.group(0)
        print(f"User {user} liked {url}")
        await reaction.message.channel.send("Thanks for the like!")

@client.event
async def on_message(message):
    print(f"Message: {message.content} Channel: {message.channel.id}")
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


def main():
    # create initial content stream rules.
    ai = Content(
        client,
        "ai",
        1047786399266512956,
        0.86,
        0.781, 
        'lang:en -is:retweet -is:reply -NFT (artificial intelligence OR technocapital OR ai safety OR superintelligence OR transhumanism OR transhumanist OR "e/acc" OR effective accelerationism) -mint -nft -crypto -bitcoin -ethereum -drop -airdrop',
    )
    ai.to_db()
    for category in ["artificial intelligence", "technocapital", "ai safety", "superintelligence", "effective accelerationism", "e/acc", "transhumanism"]:
        # just run the async command directly
        #log.info(f"adding category {category}")
        #asyncio.run(add_category(ai, category))
        pass

    whitepill = Content(
        client,
        "whitepill",
        1048696123121995836,
        0.86,
        0.781,
        "lang:en -is:retweet (whitepill OR white pill OR human flourishing OR techno optimism OR techno optimist OR techno-optimism OR futurism OR futurist OR #todayinhistory OR cybernetic) -mint -nft -crypto -bitcoin -ethereum -drop -airdrop",
    )
    whitepill.to_db()
    # TODO this really sucks.
    for category in ["white pill", "human flourishing", "good news", "techno optimism", "futurism", "today in history", "cybernetic"]:
        #log.info(f"adding category {category}")
        #asyncio.run(add_category(whitepill, category))
        pass

    # this starts everything.
    c = client.run(get_bot_token())

    # wait for all tasks to exit
    loop = asyncio.get_event_loop()
    loop.run_until_complete(activity_check())
    loop.close()


if __name__ == "__main__":
    main()
