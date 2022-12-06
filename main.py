import asyncio
import discord
import json
import re

from streamer import monitor_streamer
from streamer import contentxlr8harder

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
    if reaction.message.channel.id == 1049196639652425749:
        contentxlr8harder.handle_discord_reaction(reaction, client)
    else:
        match = re.search(r"https://twitter.com/[^/]+/status/(\d+)", reaction.message.content)
        if match:
            url = match.group(0)
            print(f"User {user} liked {url}")
            await reaction.message.channel.send("Thanks for the like!")

@client.event
async def on_message(message):
    print(f"Message: {message.content} Channel: {message.channel.id}")
    if message.author == client.user:
        return
    if not message.guild:
        await message.channel.send("Thanks for the DM!")
    

def main():
    c = client.run(get_bot_token())

    # wait for all tasks to exit
    loop = asyncio.get_event_loop()
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()


if __name__ == "__main__":
    main()
