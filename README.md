install qdrant vector database

sudo docker pull qdrant/qdrant
sudo rocker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant