import sqlite3
import glog as log


class TweetDB:
    def __init__(self):
        self.conn = sqlite3.connect("tweets.db")
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS tweets (id INTEGER PRIMARY KEY, url TEXT UNIQUE, tweet TEXT, tag TEXT, reaction TEXT default '')"
        )
        # create index on url
        self.conn.execute("CREATE INDEX IF NOT EXISTS url_index ON tweets (url)")
        self.conn.commit()

    def add(self, tweet, url, tag):
        self.conn.execute(
            "INSERT INTO tweets (url, tweet, tag) VALUES (?, ?, ?)", (url, tweet, tag)
        )
        self.conn.commit()

    def set_reaction(self, url, reaction):
        log.info("Setting reaction for %s to %s", url, reaction)
        self.conn.execute("UPDATE tweets SET reaction=? WHERE url=?", (reaction, url))
        self.conn.commit()

    def get_annotated(self, tag, reactions):
        # reactions is a list of reactions to filter on
        # e.g. ["❌", "✅"]
        # returns a list of (url, tweet, tag, reaction) tuples
        # e.g. [("https://twitter.com/elonmusk/status/123", "I love Tesla", "positive", "✅")]
        tweets = []
        for row in self.conn.execute(
            "SELECT url, tweet, tag, reaction FROM tweets WHERE tag='%s' AND reaction IN %s"
            % (tag, str(tuple(reactions)))
        ):
            tweets.append([row[0], row[1], row[2], row[3]])

        return tweets
