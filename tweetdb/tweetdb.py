# TweetDB maintains a database of tweets keyed off of their ID.  It functions as a cache, and
# also for constructing context for the AI.  It provides some convenience functions for building out
# the history for a thread.

# TODO handle full_text

import sqlite3
import json
import tweepy
import tweepy

import glog as log
log.setLevel("INFO")

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
        ) VALUES (?, ?, ?, ?, ?, ?, ?)"""

        # serialize the tweet
        serialized = json.dumps(tweet._json)
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
            tweet.created_at,
            url,
            serialized))
        self.db.commit()

