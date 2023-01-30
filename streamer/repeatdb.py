from . import embeddings


class RepeatDB:
    def __init__(self, tag, threshold=0.86):
        self.db = embeddings.EmbeddingDB(collection_name=tag + "_repeats")
        self.threshold = threshold

    async def check_repeat(self, text):
        embedding = await embeddings.get_embedding(text)
        text, score = self.db.get_nearest(embedding)
        self.db.add(text, embedding)

        if score is None:
            return False, None, None
        return score > self.threshold, text, score
