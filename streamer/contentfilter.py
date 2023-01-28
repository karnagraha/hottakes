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
        channels,
        repeat_threshold=0.86,
        filter="",
        check_classifier=True,
        check_repeats=True,
    ):

        self.tag = tag
        self.channels = channels
        self.repeat_threshold = repeat_threshold
        self.filter = filter  # this is the twitter search filter
        self.check_classifier = check_classifier
        self.check_repeats = check_repeats

        self.repeat_db = embeddings.EmbeddingDB(collection_name=self.tag + "_repeats")

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
        if self.check_repeat:
            matches_repeat, text, repeat_score = self.check_repeat(embedding)
            self.add_repeat(tweet.full_text, embedding)
            if matches_repeat:
                log.info(f"Skipping repeat: [{repeat_score}] {url}")
                return

        if not self.check_classifier:
            return url

        result = await client.predict(self.tag, tweet.full_text)
        if result is not None:
            log.info(f"Classified as {result}: {tweet.full_text}")
            score = result["score"]
            match = True if result["label"] == "positive" else False
            log.info(f"Classifier: [{match}] {score} {url}.")
        else:
            # in failure case just pass the tweet through
            match = True
            score = 1.0

        if not match:
            # remove extra whitespace from tweet (\n\t, etc)
            tweet_text = " ".join(tweet.full_text.split())
            log.info(f"Skipping negative tweet: {url} {tweet_text}")
            return
        return f"Score: [{score}] Repeat [{repeat_score}]\n{url}"
