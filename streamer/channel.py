import json
import sqlite3

import glog as log

from . import embeddings
import asyncopenai.asyncopenai as openai

class DB:
    def __init__(self):
        # sqlite database for storing content stream configuration
        self.conn = sqlite3.connect("content.db")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS content (tag TEXT PRIMARY KEY, json TEXT)")
        self.conn.commit()

    def add(self, content):
        self.cursor.execute("INSERT OR REPLACE INTO content (tag, json) VALUES (?, ?)", (content.tag, content.to_json()))
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
    def __init__(self, discord_client, tag, channel, repeat_threshold=0.86, category_threshold=0.781, filter=""):

        self.discord_client = discord_client
        self.tag = tag
        self.channel = channel
        self.category_threshold = category_threshold
        self.repeat_threshold = repeat_threshold
        self.filter = filter

        self.category_db = embeddings.EmbeddingDB(collection_name=self.tag + "_categories")
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
        return json.dumps({
            "tag": self.tag,
            "channel": self.channel,
            "category_threshold": self.category_threshold,
            "repeat_threshold": self.repeat_threshold,
            "filter": self.filter
        })

    async def get_embedding(self, text):
        r = await openai.create_embedding(text)
        if r is not None:
            embedding = r["data"][0]["embedding"]
            return embedding

    def add_category(self, category, embedding):
        return self.category_db.add(category, embedding)

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
        log.info(f"Getting embedding {url}")
        embedding = await self.get_embedding(tweet.full_text)
        log.info(f"Checking for repeat.")
        matches_repeat, text, repeat_score = self.check_repeat(embedding)
        log.info(f"Got repeat: {matches_repeat} {repeat_score}.")
        log.info(f"Saving tweet info to repeats db.")
        self.add_repeat(tweet.full_text, embedding)
        log.info(f"Checking for category.")
        matches_category, category, category_score = self.check_category(embedding)
        log.info(f"Got category: {matches_category} {category} {category_score}.")

        if not matches_repeat and matches_category:
            self.discord_client.loop.create_task(self.discord_client.get_channel(self.channel).send(
                "Similarity: " + str(repeat_score) + "\nCategory: " + category + " (" + str(category_score) + ") " + url))
        else:
            log.info(f"Skipping tweet {url} similarity {repeat_score} category {category} ({category_score})")