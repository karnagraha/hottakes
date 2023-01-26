import json
import sqlite3

import glog as log

from . import embeddings
import asyncopenai.asyncopenai as openai
from classifier import client


class DB:
    def __init__(self):
        # sqlite database for storing content stream configuration
        self.conn = sqlite3.connect("content.db")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS content (tag TEXT PRIMARY KEY, json TEXT)"
        )
        self.conn.commit()

    def add(self, content):
        self.cursor.execute(
            "INSERT OR REPLACE INTO content (tag, json) VALUES (?, ?)",
            (content.tag, content.to_json()),
        )
        self.conn.commit()

    def get(self, tag, discord_client):
        self.cursor.execute("SELECT * FROM content WHERE tag=?", (tag,))
        row = self.cursor.fetchone()
        if row is None:
            return None
        else:
            return Content.from_json(row["json"], discord_client)

    def get_all(self, discord_client):
        self.cursor.execute("SELECT * FROM content")
        rows = self.cursor.fetchall()
        return [Content.from_json(row["json"], discord_client) for row in rows]


class Content:
    """Content represents one particular content stream, and holds configuration for the twitter filter, related discord config
    and tuning parameters for the embedding model. It can be serialized and deserialized from a sqlite config database. A stream is always
    associated with a single discord channel."""

    def __init__(
        self,
        discord_client,
        tag,
        channel,
        repeat_threshold=0.86,
        category_threshold=0.781,
        filter="",
    ):

        self.discord_client = discord_client
        self.tag = tag
        self.channel = channel
        self.category_threshold = category_threshold
        self.repeat_threshold = repeat_threshold
        self.filter = filter

        self.category_db = embeddings.EmbeddingDB(
            collection_name=self.tag + "_categories"
        )
        self.repeat_db = embeddings.EmbeddingDB(collection_name=self.tag + "_repeats")

    @classmethod
    def from_json(cls, json_str, discord_client):
        return cls(discord_client=discord_client, **json.loads(json_str))

    @classmethod
    def from_db(cls, tag, discord_client):
        db = DB()
        return db.get(tag)

    def to_db(self):
        db = DB()
        db.add(self)

    def to_json(self):
        # convert to json representation
        return json.dumps(
            {
                "tag": self.tag,
                "channel": self.channel,
                "category_threshold": self.category_threshold,
                "repeat_threshold": self.repeat_threshold,
                "filter": self.filter,
            }
        )

    async def get_embedding(self, text):
        r = await openai.create_embedding(text)
        if r is not None:
            try:
                embedding = r["data"][0]["embedding"]
            except (KeyError, IndexError) as e:
                log.error(f"Error getting embedding: {e}")
            else:
                return embedding
        return None

    def add_category(self, category, embedding):
        return self.category_db.add(category, embedding)

    def clear_categories(self):
        self.category_db.reset()

    def check_category(self, embedding):
        """Returns whether the embedding matches a category, and the nearest category name and score."""
        category, score = self.category_db.get_nearest(embedding)
        if score is None:
            return False, None, None
        return score > self.category_threshold, category, score

    def add_repeat(self, text, embedding):
        return self.repeat_db.add(text, embedding)

    def check_repeat(self, embedding):
        """Returns whether the embedding matches a repeat, and the nearest repeat text and score."""
        text, score = self.repeat_db.get_nearest(embedding)
        if score is None:
            return False, None, None
        return score > self.repeat_threshold, text, score

    def set_filter(self, filter):
        """Sets the filter string for this content stream"""
        self.filter = filter
        self.to_db()
        # TODO: This needs to get saved to a database.
        # TODO: This needs to get communicated back to twitter.
        raise UnimplementedError()

    def get_filter(self):
        return self.filter

    async def handle_tweet(self, tweet):
        url = f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"
        log.info(f"Got tweet {url}")
        embedding = await self.get_embedding(tweet.full_text)
        if embedding is None:
            log.error(f"Error getting embedding for {url}")
            return
        matches_repeat, text, repeat_score = self.check_repeat(embedding)
        log.info(f"Repeat? {matches_repeat} {repeat_score}.")
        self.add_repeat(tweet.full_text, embedding)

        if self.tag == "ai":
            result = await client.predict(self.tag, tweet.full_text)
            if result is not None:
                log.info(f"Classified as {result}: {tweet.full_text}")
                if result["label"] == "positive":
                    matches_category = True
                    category = "positive"
                    category_score = 1.0
                else:
                    matches_category = False
                    category = "negative"
                    category_score = 1.0
            else:
                matches_category = True  # TODO probably change this
                category = "failure"
                category_score = 1.0
        else:
            result = "n/a"
            matches_category, category, category_score = self.check_category(embedding)

        log.info(f"Got category: {matches_category} {category} {category_score}.")

        if not matches_repeat and matches_category:
            self.discord_client.loop.create_task(
                self.discord_client.get_channel(self.channel).send(
                    "Match: "
                    + str(result)
                    + "\nSimilarity: "
                    + str(repeat_score)
                    + "\nCategory: "
                    + category
                    + " ("
                    + str(category_score)
                    + ") "
                    + url
                )
            )
        else:
            log.info(
                f"Skipping tweet {url} similarity {repeat_score} category {category} ({category_score})"
            )
