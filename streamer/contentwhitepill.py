import datetime
import glog as log

from . import gpt
from . import embeddings

# singleton
db = None

def get_db():
    global db
    if db is not None:
        return db
    else:
        db = embeddings.EmbeddingDB()
        return db

async def classify(tweet):
    prompt = """We want to identify the absolute best, most interesting and inspiring tweets.
We are looking for "whitepill" content.  Whitepill means it is an antidote to cynicism, doomerism and blackpill thinking. Whitepill means it will get people excited about life, the future, and the potential of humanity. It must also fit within our content policy.
CONTENT POLICY:
- No obvious press releases, no obvious marketing.
- No wokeness, racial issues, or social issues.
- Definitely include: good whitepill tweets, tweets that are optimistic about the future, and tweets celebrating the past.

Consider the following tweet.
    
TWEET:
""" + tweet + """

Was this a good inspiring tweet? Answer with "yes" or "no"."""
    return await gpt.send_yn_prompt(prompt)



async def handle_tweet(tweet, client):
    url = f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"

    db = get_db()
    embedding = await db.get_embedding(tweet.full_text)
    distance = None
    if embedding is not None:
        text, distance = db.get_nearest(embedding)
        log.info(f"Closest match for '{tweet.full_text}' is '{text}' with distance {distance}")
        db.add(tweet.full_text, embedding)

    if distance is None or distance > 0.5:
        client.loop.create_task(client.get_channel(1048696123121995836).send(url))