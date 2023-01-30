import glog as log


class EventFilter:
    """EventFilter is responsible for filtering tweets. It holds the twitter search filter
    configuration and the logic for further filtering tweets by tweet content.
    Filtering types:
    - classifier: if specified use the classifier to filter tweets.
    - repeat_db: if specified use the repeat_db to filter tweets."""

    def __init__(
        self,
        tag,
        channels,
        filter="",
        repeat_db=None,
        classifier=None,
    ):
        self.tag = tag
        self.channels = channels
        self.filter = filter  # this is the twitter search filter

        self.classifier = classifier
        self.repeat_db = repeat_db

    def get_filter(self):
        return self.filter

    def get_channels(self):
        return self.channels

    async def handle_event(self, event):
        """Handles en event from the twitter feed.  Event is a dict containing the url and the text
        of a tweet.  Returns the content to be sent to the channel or None if the event should be
        ignored."""
        url = event["url"]
        text = event["text"]
        response = ""

        if self.classifier:
            try:
                result = await self.classifier.predict(self.tag, text)
            except Exception as e:
                log.error(f"Got exception from classifier: {e}")
                result = None

            if result:
                score = result["score"]
                match = True if result["label"] == "positive" else False
                log.info(f"[{self.tag}] classifier [{match}] {score} {url}")
            else:
                # in failure case just pass the tweet through
                log.info(f"[{self.tag}] classifier failed for {url}")
                match = True
                score = 1.0

            if not match:
                return
            response = f"Score:[{score}]"

        if self.repeat_db:
            matches_repeat, text, repeat_score = await self.repeat_db.check_repeat(text)
            if matches_repeat:
                log.info(f"[{self.tag}] repeat skipped {repeat_score} {url}")
                return
            response = f"{response} Repeat:[{repeat_score}]"

        response = f"{response}\n{url}"
        return response
