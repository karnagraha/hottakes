import asyncio
import discord
import json

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
async def on_message(message):
    if message.author == client.user:
        return
    # print message and channel id
    print(f"Message: {message.content} Channel: {message.channel.id}")


def main():
    c = client.run(get_bot_token())

    # wait for all tasks to exit
    loop = asyncio.get_event_loop()
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()


if __name__ == "__main__":
    main()

