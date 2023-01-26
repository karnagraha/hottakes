import glog as log

from . import embeddings
import asyncopenai.asyncopenai as openai
from classifier import client


class ContentFilter:
    """ContentFilter is responsible for filtering tweets. It holds the twitter search filter
    configuration and the logic for further filtering tweets by tweet content."""

    def __init__(
        self,
        tag,
        channel,
        repeat_threshold=0.86,
        category_threshold=0.781,
        filter="",
    ):

        self.tag = tag
        self.channel = channel
        self.category_threshold = category_threshold
        self.repeat_threshold = repeat_threshold
        self.filter = filter  # this is the twitter search filter

        self.category_db = embeddings.EmbeddingDB(
            collection_name=self.tag + "_categories"
        )
        self.repeat_db = embeddings.EmbeddingDB(collection_name=self.tag + "_repeats")

    def add_category(self, category, embedding):
        return self.category_db.add(category, embedding)

    def check_category(self, embedding):
        """Returns whether the embedding matches a category, and the nearest category name and score."""
        category, score = self.category_db.get_nearest(embedding)
        if score is None:
            return False, None, None
        return score > self.category_threshold, category, score

    def clear_categories(self):
        self.category_db.reset()

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
        embedding = await embeddings.get_embedding(tweet.full_text)
        if embedding is None:
            log.error(f"Error getting embedding for {url}")
            return
        matches_repeat, text, repeat_score = self.check_repeat(embedding)
        log.info(f"Repeat? {matches_repeat} {repeat_score} {url}.")
        self.add_repeat(tweet.full_text, embedding)

        if self.tag in ["ai", "companies"]:
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

        log.info(f"category: {matches_category} {category} {category_score} {url}.")

        if not matches_repeat and matches_category:
            return (
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
        else:
            log.info(
                f"Skipping tweet {url} similarity {repeat_score} category {category} ({category_score})"
            )
