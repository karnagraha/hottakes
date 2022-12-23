import asyncio
import datetime
import json
import re
import glog as log

import discord
from streamer import monitor_streamer


client = discord.Client(intents=discord.Intents.default())


def get_bot_token():
    with open("discord_secrets.json") as f:
        secrets = json.load(f)
    return secrets["bot_token"]


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")
    asyncio.get_event_loop().create_task(monitor_streamer.monitor_stream(client))

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

def main():
    c = client.run(get_bot_token())

    # wait for all tasks to exit
    loop = asyncio.get_event_loop()
    loop.run_until_complete(activity_check())
    loop.close()


if __name__ == "__main__":
    main()
