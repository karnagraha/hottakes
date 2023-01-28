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

    async def handle_event(self, event):
        url = event["url"]
        text = event["text"]

        if self.check_classifier:
            try:
                result = await client.predict(self.tag, text)
            except Exception as e:
                log.error(f"Got exception from classifier: {e}")
                result = None

            if result is not None:
                log.info(f"Classified as {result}: {text}")
                score = result["score"]
                match = True if result["label"] == "positive" else False
                log.info(f"Classifier: [{match}] {score} {url}.")
            else:
                # in failure case just pass the tweet through
                match = True
                score = 1.0

            if not match:
                # remove extra whitespace from tweet (\n\t, etc)
                clean_text = " ".join(text.split())
                log.info(f"Skipping negative tweet: {url} {clean_text}")
                return

        if self.check_repeat:
            embedding = await embeddings.get_embedding(text)
            if embedding is not None:
                # check if the repeat is in the repeat db, then add it.
                try:
                    matches_repeat, text, repeat_score = self.check_repeat(embedding)
                    self.add_repeat(text, embedding)
                except Exception as e:
                    log.info(f"Got exception from embeddings: {e}")
                    # on embeddings db error, ignore repeat logic.
                    matches_repeat = False
                    repeat_score = 0.0

                if matches_repeat:
                    log.info(f"Skipping repeat: [{repeat_score}] {url}")
                    return
            else:
                # in failure case we just pass the tweet through.
                log.error(f"Error getting embedding for {url}")
                repeat_score = 0.0

        return f"Score:[{score}] Repeat:[{repeat_score}]\n{url}"
