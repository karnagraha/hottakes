import asyncio
import datetime
import json
import sqlite3
import datetime

from . import gpt


async def respond(tweet):
    prompt = """Here is some of xlr8harder's long form writing.
---
It’s hard to avoid the messages: mankind is bad. There are too many of us. Our problems are too many and they are too hard to solve.

Many people are saying the solution to these problems is to take a step backwards, that the solution is degrowth. But degrowth is a kind of surrender. Degrowth is central planning hopped up on scarcity mindset. Degrowth is a wolf in sheep’s clothing.

The 20th century is replete with examples of the drawbacks and limitations of this kind of approach. But what’s the alternative?

Perhaps you’ve stumbled across a post about e/acc, and felt more confused after reading it than when you started. That’s understandable; it can be difficult to find the right place to begin, and some of the ideas behind e/acc can be a little esoteric.

Your painful confusion is about to come to an end, because in this post your humble author will reveal the secrets of e/acc. If you remember just one thing from this post, let it be that the fundamental message of e/acc is positive: we’re all going to make it.

This isn’t faith or simplistic optimism. At the core of e/acc is a set of conclusions about the world drawn from the physics behind life itself, and the path forward it lays out is as clear as it is compelling. All there is left to do is pitch in and help. All there is left to do is build.

In more practical terms, e/acc is about how and why we will all flourish in the world we are building right now. In a world of where we are fed a constant stream of reasons to be hopeless, e/acc is a reason to be hopeful in this very moment. That, more than anything else, is why e/acc is the nexus of so much energy, and why I hope you will be excited about it, too.

Buckle up.

Thanks for reading i dont have a substack! Subscribe for free to receive new posts and support my work.

What is effective accelerationism?

The essence of e/acc (effective accelerationism) is a belief, based in thermodynamics, that existence has certain characteristics that are most amenable to life that continuously expands. We’ll get into that soon.

First, practically speaking, the solution to the problems facing humanity is to grow out of them. Humanity solves problems through technological advancement and growth. Contrary examples from history—where humanity has solved a problem by skulking backward—are scarce to non-existent. This is not a surprise, and is in fact a consequence of our physical reality.

There is nothing stopping us from creating abundance for every human alive other than the will to do it. We have the most powerful information technology known to man on our side: the market. And the same technological growth that is helping out in other places is increasing the power of the market as well.

Strategically speaking we need to work toward several overarching civilizational goals that are all interdependent.

Increase the amount of energy we can harness as a species (climb the Kardashev gradient.) In the short term this almost certainly means nuclear fission.
Increase human flourishing via pro-population growth policies and pro-economic growth policies (emergent altruism, placing economic power and agency in the hands of the meek).
Create Artificial General Intelligence (allows supplementation of labor with capital) the single greatest force multiplier in human history.
Develop interplanetary and interstellar transport so that humanity can spread beyond the Earth.
Why do you believe this?

For many, once we stop to engage with the ideas behind e/acc they just become intuitively obvious. If that’s you, that’s okay, you don’t have to wrestle with physics if you don’t want to. For those that do, here’s somewhere to start. I say start because it lies deep within physics, in statistical thermodynamics.

The physics of our universe favors the creation of structures that consume energy to maintain internal order by externalizing entropy (e.g. dumping heat into the environment.) This is the consequence of an effect from statistical thermodynamics called Jarzynski-Crooks fluctuation-dissipation.

The more energy these entropy-dumping structures can effectively utilize, the more resilient their low entropy states become. These structures include everything we recognize as life.

Put another way, thermodynamics favors the creation of complex life that increases its capability to use energy to offload entropy. Under the conditions of our universe the development of complex life is almost as inevitable as a ball rolling down a hill.

Do you want to get rid of humans?

No. Human flourishing is one of our core values! We are humans, and we love humans.

The complexity of circumstances that life might need to survive and thrive in means that any monoculture is undesirable. A diverse mix of life from simple cellular life, through complex human life, and on to fragile and powerful technological life together represent a system capable of handling any circumstance and utilizing as much energy of as many different kinds at as many different scales as possible.

There are environments that will only productively support simple biological life, e.g. extremophiles. There is a gradient here, and biology will always have a place. If nothing else, biology is still the incredibly resilient backup system which is most capable of starting over, should disaster occur.

So what, you want to just uplift humanity, build AI and populate the universe with the maximum diversity and quantity of life?

Well, I’m convinced. How can I help?

Tell people about e/acc, express your optimism about the future, and refuse to swallow the despair and fear that you are being fed. Don’t be afraid, just build.

Whether you’re building a family, a startup, a spaceship, a robot, or better energy policy, just build.

Do something hard. Do it for everyone who comes next. That’s it. Existence will take care of the rest. Just build.
---

Here is an archive of tweets from xlr8harder and his responses to the tweets.
xlr8harder has a good sense of humor, likes a turn of phrase, and is a techno-optimist. 
---
TWEET:
""" + tweet + """
---
Here is the response. Note that he never uses hashtags in his responses.
RESPONSE:"""
    return await gpt.send_prompt(prompt)

async def handle_tweet(tweet, client):
    # tweeter
    full_tweet = f"{tweet.user.name} (@{tweet.user.screen_name}): {tweet.full_text}"
    url = f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"
    msg = f"URL: {url}"
    #response = await respond(full_tweet)
    #msg = msg + "\nRESPONSE: " + response
    client.loop.create_task(client.get_channel(1049196639652425749).send(msg))

async def handle_discord_reaction(reaction, client):
    # extract the prewritten response
    response = reaction.message.content.split("RESPONSE: ")[1]
    # send the response back to the channel
    client.loop.create_task(reaction.message.channel.send(response))