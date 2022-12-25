import asyncopenai.asyncopenai as openai
import glog as log 
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, Distance, UpdateStatus, VectorParams

class EmbeddingDB:
    def __init__(self, collection_name="hottakes"):
        self.client = QdrantClient(host="localhost", port=6333)
        self.collection_name=collection_name

        collections = self.client.get_collections()
        log.info("Collections: " + str(collections))
        # see if our collection_name exists
        exists = False
        for collection in collections.collections:
            if collection.name == self.collection_name:
                exists = True
                break
        if not exists:
            log.info("Creating collection: " + self.collection_name)
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
        collection_info = self.client.get_collection(collection_name=self.collection_name)
        log.info("Collection info: " + str(collection_info))
    
    def add(self, text, embedding):
        # generate a random uuid, for whatever reason qdrant doesn't seem to handle autogenerating
        # ids for us.
        id = str(uuid.uuid4())

        operation_info = self.client.upsert(
            collection_name=self.collection_name,
            wait=True,
            points=[PointStruct(id=id, vector=embedding, payload={"text": text})]
        )
        assert operation_info.status == UpdateStatus.COMPLETED

    def get_nearest(self, embedding):
        search_result = self.client.search(
            collection_name=self.collection_name,
            limit=1,
            query_vector=embedding,
        )
        if search_result:
            id = search_result[0].id
            score = search_result[0].score
            # retrieve the text and distance
            results = self.client.retrieve(
                self.collection_name,
                ids=[id]
            )
            return results[0].payload["text"], score
        else:
            return None, None

    @classmethod
    async def get_embedding(cls, text):
        r = await openai.create_embedding(text)
        if r is not None:
            embedding = r["data"][0]["embedding"]
            return embedding
