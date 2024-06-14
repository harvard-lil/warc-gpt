from abc import ABC, abstractmethod
from typing import Dict, List, Mapping, Sequence, TypedDict, Union

Embedding = Sequence[float]
Metadata = Mapping[str, Union[str, int, float, bool]]


class StorageResponse(TypedDict):
    ids: List[str]
    embeddings: List[Embedding]
    documents: List[str]
    metadatas: List[Metadata]


class VectorStorage(ABC):
    """
    Abstract class to define a common interface for vector databases.
    """

    @abstractmethod
    def add(
        self,
        documents: List[str],
        embeddings: List[Sequence[float]],
        metadatas: List[Dict],
        ids: List[str],
    ) -> None:
        """Stores the data to a vector storage."""
        raise NotImplementedError()

    @abstractmethod
    def get_all(self) -> StorageResponse:
        """Returns all the data stored in vector storage."""
        raise NotImplementedError()

    @abstractmethod
    def search(self, query_embedding: Embedding, limit: int) -> StorageResponse:
        """Returns semantically similar data from a vector storage with limit."""
        raise NotImplementedError()

    @classmethod
    def make_storage(cls, name, *args, **kwargs):
        for sc in cls.__subclasses__():
            if sc.__name__.lower() == name.lower():
                return sc(*args, **kwargs)
        raise ValueError("Vector storage implemementation not found.")
