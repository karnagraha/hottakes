import os
import datetime
import email.utils
import unittest

from tweetdb import TweetDB
import tweepy

# mock implementation of the tweepy.API class
class MockAPI:
    def get_status(self, id, tweet_mode="unused"):

        # special handling for tweet 456 which is always a reply to tweet 789
        in_reply_to_status_id = None
        if id == 456:
            in_reply_to_status_id = 789

        return tweepy.models.Status().parse(None, {
            "id": id,
            "text": f"Tweet {id}",
            "in_reply_to_status_id": in_reply_to_status_id,
            # tweepy uses email.utils.parsedate_to_datetime to parse the date string.
            "created_at": "Thu, 08 Dec 2022 11:54:02 +0200",
            "user": {
                "screen_name": "test_user"
            },
        })

class TestTweetDB(unittest.TestCase):
    def setUp(self):
        self.api = MockAPI()
        db = "test.sqlite"
        if os.path.exists(db):
            os.unlink(db)
        self.db = TweetDB(self.api, db)

    def test_get_tweet_from_api(self):
        tweet = self.db.get_tweet_from_api(123)
        print(tweet)

        self.assertEqual(tweet.id, 123)
        self.assertEqual(tweet.text, "Tweet 123")
        self.assertEqual(tweet.user.screen_name, "test_user")

    def test_get_tweet_from_db(self):
        # ensure tweet is cached in db
        _ = self.db.get_tweet(123)

        tweet = self.db.get_tweet_from_db(123)
        self.assertEqual(tweet.id, 123)
        self.assertEqual(tweet.text, "Tweet 123")
        self.assertEqual(tweet.user.screen_name, "test_user")

    def test_get_tweet_uncached(self):
        tweet_id = 1829192819
        tweet = self.db.get_tweet(tweet_id)
        self.assertEqual(tweet.id, tweet_id)
        self.assertEqual(tweet.text, f"Tweet {tweet_id}")
        self.assertEqual(tweet.user.screen_name, "test_user")

    def test_get_tweet_cached(self):
        tweet_id = 456
        # prime cache
        _ = self.db.get_tweet(tweet_id)
        tweet = self.db.get_tweet(tweet_id)
        self.assertEqual(tweet.id, tweet_id)
        self.assertEqual(tweet.text, f"Tweet {tweet_id}")
        self.assertEqual(tweet.user.screen_name, "test_user")

    def test_get_tweet_in_reply_to(self):
        tweet_id = 456
        # put parent in db
        _ = self.db.get_tweet(789)
        tweet = self.db.get_tweet(tweet_id)
        self.assertEqual(tweet.id, tweet_id)
        self.assertEqual(tweet.text, f"Tweet {tweet_id}")
        self.assertEqual(tweet.user.screen_name, "test_user")
        self.assertEqual(tweet.in_reply_to_status_id, 789)

    def test_get_tweet_in_reply_to_uncached(self):
        tweet_id = 456
        tweet = self.db.get_tweet(tweet_id)
        self.assertEqual(tweet.id, tweet_id)
        self.assertEqual(tweet.text, f"Tweet {tweet_id}")
        self.assertEqual(tweet.user.screen_name, "test_user")
        self.assertEqual(tweet.in_reply_to_status_id, 789)


    def test_get_tweet_with_context(self):
        tweet_id = 456
        tweets = self.db.get_tweet_with_context(tweet_id)

        self.assertEqual(len(tweets), 2)
        self.assertEqual(tweets[0].id, 789)
        self.assertEqual(tweets[0].text, "Tweet 789")
        self.assertEqual(tweets[0].user.screen_name, "test_user")
        self.assertEqual(tweets[1].id, tweet_id)
        self.assertEqual(tweets[1].text, f"Tweet {tweet_id}")
        self.assertEqual(tweets[1].user.screen_name, "test_user")

