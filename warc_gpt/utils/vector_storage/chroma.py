from os import environ
from typing import Dict, List, Sequence

import chromadb
from warc_gpt.utils.vector_storage.base import VectorStorage, StorageResponse


class Chroma(VectorStorage):
    def __init__(self):
        chroma_client = chromadb.PersistentClient(
            path=environ["VECTOR_SEARCH_PATH"],
            settings=chromadb.Settings(anonymized_telemetry=False),
        )

        self.chroma_collection = chroma_client.get_or_create_collection(
            name=environ["VECTOR_SEARCH_COLLECTION_NAME"],
            metadata={"hnsw:space": environ["VECTOR_SEARCH_DISTANCE_FUNCTION"]},
        )

    def add(
        self,
        documents: List[str],
        embeddings: List[Sequence[float]],
        metadatas: List[Dict],
        ids: List[str],
    ) -> None:
        return self.chroma_collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

    def get_all(self) -> StorageResponse:
        return self.chroma_collection.get(include=["metadatas", "documents", "embeddings"])

    def search(self, query_embedding: Sequence[float], limit: int) -> StorageResponse:
        results = self.chroma_collection.query(
            query_embeddings=query_embedding,
            n_results=limit,
            include=["documents", "metadatas", "embeddings"],
        )

        return {
            "documents": results["documents"][0],
            "embeddings": results["embeddings"][0],
            "metadatas": results["metadatas"][0],
            "ids": results["ids"][0],
        }
