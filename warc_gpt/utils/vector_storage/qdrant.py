from copy import deepcopy
from os import environ, getenv
from typing import Dict, List, Sequence
import uuid

from qdrant_client import QdrantClient, models
from warc_gpt.utils.vector_storage.base import VectorStorage, StorageResponse

ID_KEY = "_id"
DOCUMENT_KEY = "_document"
SCROLL_SIZE = 64


class Qdrant(VectorStorage):
    def __init__(self):
        self.collection_name = environ["VECTOR_SEARCH_COLLECTION_NAME"]
        self.client = QdrantClient(
            location=getenv("QDRANT_LOCATION"),
            port=int(getenv("QDRANT_PORT", 6333)),
            grpc_port=int(getenv("QDRANT_GRPC_PORT", 6334)),
            prefer_grpc=bool(getenv("QDRANT_PREFER_GRPC", False)),
            https=bool(getenv("QDRANT_HTTPS", False)),
            api_key=getenv("QDRANT_API_KEY"),
            prefix=getenv("QDRANT_PREFIX"),
            timeout=int(getenv("QDRANT_TIMEOUT", 0)) or None,
            host=getenv("QDRANT_HOST"),
            path=getenv("QDRANT_PATH"),
        )

    def add(
        self,
        documents: List[str],
        embeddings: List[Sequence[float]],
        metadatas: List[Dict],
        ids: List[str],
    ) -> None:
        self._ensure_collection(size=len(embeddings[0]))
        payloads = [
            {**metadata, ID_KEY: id, DOCUMENT_KEY: document}
            for document, metadata, id in zip(documents, metadatas, ids)
        ]

        # Qdrant onlly allows UUIDs and unsigned integers as point IDs
        # https://qdrant.tech/documentation/concepts/points/#point-ids
        ids = [uuid.uuid4().hex for _ in ids]

        self.client.upsert(
            self.collection_name,
            points=models.Batch(ids=ids, vectors=embeddings, payloads=payloads),
        )

    def get_all(self) -> StorageResponse:
        points = self._scroll_points()

        ids, embeddings, documents, metadatas = [], [], [], []

        for point in points:
            payload = deepcopy(point.payload)
            ids.append(payload.pop(ID_KEY))
            documents.append(payload.pop(DOCUMENT_KEY))
            metadatas.append(payload)
            embeddings.append(point.vector)

        return {
            "documents": documents,
            "embeddings": embeddings,
            "ids": ids,
            "metadatas": metadatas,
        }

    def search(self, query_embedding: Sequence[float], limit: int) -> StorageResponse:
        points = self.client.search(
            self.collection_name,
            query_vector=query_embedding,
            with_payload=True,
            with_vectors=True,
            limit=True,
        )
        ids, embeddings, documents, metadatas = [], [], [], []

        for point in points:
            payload = deepcopy(point.payload)
            ids.append(payload.pop(ID_KEY))
            documents.append(payload.pop(DOCUMENT_KEY))
            metadatas.append(payload)
            embeddings.append(point.vector)

        return {
            "documents": documents,
            "embeddings": embeddings,
            "ids": ids,
            "metadatas": metadatas,
        }

    def _scroll_points(self) -> List[models.Record]:
        """
        Scroll through and return all points in a collection
        """

        from qdrant_client import grpc

        records = []
        next_offset = None
        stop_scrolling = False
        while not stop_scrolling:
            response, next_offset = self.client.scroll(
                self.collection_name,
                limit=SCROLL_SIZE,
                offset=next_offset,
                with_payload=True,
                with_vectors=True,
            )

            stop_scrolling = next_offset is None or (
                isinstance(next_offset, grpc.PointId)
                and next_offset.num == 0
                and next_offset.uuid == ""
            )

            records.extend(response)

        return records

    def _ensure_collection(self, size: int):
        if not self.client.collection_exists(self.collection_name):
            distance = self._convert_metric(getenv("VECTOR_SEARCH_DISTANCE_FUNCTION", "cosine"))
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=size, distance=distance),
            )

    def _convert_metric(self, metric: str):
        from qdrant_client.models import Distance

        mapping = {
            "cosine": Distance.COSINE,
            "l2": Distance.EUCLID,
            "ip": Distance.DOT,
        }

        if metric not in mapping:
            raise ValueError(f"Unsupported Qdrant similarity metric: {metric}")

        return mapping[metric]
