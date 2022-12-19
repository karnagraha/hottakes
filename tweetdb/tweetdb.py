# TweetDB maintains a database of tweets keyed off of their ID.  It functions as a cache, and
# also for constructing context for the AI.  It provides some convenience functions for building out
# the history for a thread.

# TODO handle full_text

import sqlite3
import json
import tweepy
import time

import glog as log
log.setLevel("INFO")

def get_api():
    """Returns a tweepy.API object for the authenticated user"""
    bearer_token = json.load(open("twitter_secrets.json"))["bearer_token"]
    auth = tweepy.OAuth2BearerHandler(bearer_token)
    api = tweepy.API(auth)
    return api

class TweetDB:
    def __init__(self, api, dbfile="tweetdb.sqlite"):
        """Create a new TweetDB object.  This will create a new sqlite database
        if one does not exist.  api is a tweepy.API object.  dbfile is the path"""
        self.api = api
        self.dbfile = dbfile
        self.db = sqlite3.connect(dbfile)
        self.c = self.db.cursor()
        self.c.execute("""
            CREATE TABLE IF NOT EXISTS tweets (
                id INTEGER PRIMARY KEY,
                user TEXT,
                parent_id INTEGER,
                parent_user TEXT,
                timestamp DATETIME,
                last_update DATETIME,
                url TEXT,
                serialized TEXT)""")
        # create some indexes
        self.c.execute("CREATE INDEX IF NOT EXISTS parent_id ON tweets (parent_id)")
        self.c.execute("CREATE INDEX IF NOT EXISTS user ON tweets (user)")
        self.c.execute("CREATE INDEX IF NOT EXISTS parent_user ON tweets (parent_user)")
        self.c.execute("CREATE INDEX IF NOT EXISTS timestamp ON tweets (timestamp)")
        self.db.commit()

    def get_tweet_from_api(self, id):
        """Get a tweet from twitter, bypassing the database.
        Returns a tweepy.models.Status object, or None if error."""
        # use tweepy api to retrieve the tweet by id
        log.info(f"Retrieving tweet {id} from Twitter")
        try:
            tweet = self.api.get_status(id, tweet_mode="extended")
        except tweepy.TweepyException as e:
            log.warn(f"Failed to retrieve tweet {id}: {e}")
            return None
        return tweet

    def get_tweet_from_db(self, id):
        log.info(f"Getting tweet {id} from DB")
        self.c.execute("SELECT serialized FROM tweets WHERE id = ?", (id,))
        tweet = self.c.fetchone()
        if tweet:
            # deserialize tweepy status object from json
            tweet = json.loads(tweet[0])
            tweet = tweepy.models.Status().parse(self.api, tweet)
        else:
            tweet = None
        return tweet

    def get_tweet(self, id):
        """Get a tweet from the database.  If it doesn't exist, retrieve it from Twitter.
        Returns a tweepy.models.Status object, or None if error."""
        tweet = self.get_tweet_from_db(id)
        if not tweet:
            log.info(f"Tweet {id} not found in DB, retrieving from Twitter")
            tweet = self.get_tweet_from_api(id)
            if tweet:
                self.save_tweet(id, tweet)
            else:
                log.info(f"Couldn't get_tweet {id} from Twitter or DB")
                return None
        return tweet

    def get_tweet_with_context(self, id):
        """Gets a list of a tweet in thread context, with all recursive parent tweets. The list
        is in order with the root tweet first and the actual requested tweet last. Returns an
        empty list if there is no match, and a partial list """
        tweets = []
        tweet = self.get_tweet(id)
        if not tweet:
            log.warn(f"Failed to get tweet {id} with context")
            return tweets

        tweets.append(tweet)
        while tweet.in_reply_to_status_id:
            tweet = self.get_tweet(tweet.in_reply_to_status_id)
            if not tweet:
                log.warn(f"Failed to get parent tweet {id} with context")
                break
            tweets.insert(0, tweet)
        return tweets

    def update_tweets(self, delta=3600, delay=5):
        """Update all tweets in the database that are at least an hour old and have not been updated."""
        # ensure the creation time is >1 hour ago, and the update time is null or <1 hour from the creation time.
        tweets = self.c.execute("SELECT id FROM tweets WHERE timestamp < datetime('now', '-1 hour') AND (last_update IS NULL OR last_update < datetime(timestamp, '+1 hour'))")

        for tweet in tweets.fetchall():
            log.info(f"Updating tweet {tweet[0]}")
            update = self.get_tweet_from_api(tweet[0])
            if update is not None:
                self.update_tweet(update)
            else:
                self.update_tweet_timestamp(tweet[0])
            time.sleep(delay)
    

    def update_tweet(self, tweet):
        """Update a tweet in the database.  This will update the last_update timestamp."""
        query = """
        UPDATE tweets SET
            last_update = datetime('now'),
            serialized = ?
        WHERE id = ?"""
        self.c.execute(query, (json.dumps(tweet._json), tweet.id))
        self.db.commit()

    def update_tweet_timestamp(self, tweetid):
        """Update the timestamp of a tweet in the database.  This will update the timestamp
        to the current time."""
        query = """
        UPDATE tweets SET
            timestamp = datetime('now')
        WHERE id = ?"""
        self.c.execute(query, (tweetid, ))
        self.db.commit()



    def save_tweet(self, id, tweet):
        """Save a tweet to the database.  If the tweet is a reply, recursively save the parent tweet
        if it does not already exist in the db."""
        query = """
        INSERT INTO tweets (
            id,
            user,
            parent_id,
            parent_user,
            timestamp,
            url,
            serialized
        ) VALUES (?, ?, ?, ?, datetime('now'), ?, ?)"""

        # serialize the tweet
        url = f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"

        # this will recurse a lot when we have a long thread we haven't seen yet.
        # which should be fine until we hit a thread that exceeds the max recursion depth
        parent_user = None
        if tweet.in_reply_to_status_id:
            log.info(f"Saved tweet {id} is a reply to {tweet.in_reply_to_status_id}, fetching that tweet.")
            parent = self.get_tweet(tweet.in_reply_to_status_id)
            if parent:
                parent_user = parent.user.screen_name
            else:
                log.warn(f"Failed to retrieve parent tweet {tweet.in_reply_to_status_id}, skipping")

        log.info(f"Saving tweet {id} to DB")
        self.c.execute(query, (
            id,
            tweet.user.screen_name,
            tweet.in_reply_to_status_id,
            parent_user,
            url,
            json.dumps(tweet._json)))
        self.db.commit()

if __name__ == "__main__":
    api = get_api()
    db = TweetDB(api)
    print("Updating tweets...")
    db.update_tweets()
