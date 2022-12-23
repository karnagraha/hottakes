import datetime
import glog as log

from . import gpt
from . import embeddings

NAME = "whitepill"
CHANNEL = 1048696123121995836
CATEGORIES = [
        "white pill",
        "human flourishing",
        "good news",
        "techno optimism",
        "futurism",
        "today in history", 
        "cybernetic",
]


# singleton
db = None
category_db = None

def get_db():
    global db
    if db is not None:
        return db
    else:
        db = embeddings.EmbeddingDB()
        return db

def get_category_db():
    global category_db
    if category_db is not None:
        return category_db
    else:
        category_db = embeddings.EmbeddingDB(collection_name="categories_whitepill")
        return category_db

async def setup_categories():
    category_db = get_category_db()

    for category in CATEGORIES:
        embedding = await category_db.get_embedding(category)
        category_db.add(category, embedding)


async def handle_tweet(tweet, client):
    url = f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"

    db = get_db()
    embedding = await db.get_embedding(tweet.full_text)

    score = None
    category = category_score = None
    if embedding is not None:
        # categorize
        category_db = get_category_db()
        category, category_score = category_db.get_nearest(embedding)
        text, score = db.get_nearest(embedding)
        db.add(tweet.full_text, embedding)

    if (score is None or score < 0.86) and category_score > 0.78:
        client.loop.create_task(client.get_channel(CHANNEL).send(
            "Similarity: " + str(score) + "\nCategory: " + category + " (" + str(category_score) + ") " + url))
    else:
        log.info(f"Skipping tweet {url} similarity {score} category {category} ({category_score})")